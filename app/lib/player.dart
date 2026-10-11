// 변환 결과 다운로드 → 기기 저장 → 재생 (mobile-deploy 스킬 step 4).
// - 장문: /download/{jobId} (완료될 때까지 폴링 후 다운로드)
// - 단문: /download/single/{fileId}
// - 이어듣기: pos_<key> 초 단위 저장/복원
// - 백그라운드: Android는 audio_service(알림·잠금화면 컨트롤),
//   그 외는 just_audio 직접 재생. 화면을 닫아도 재생 유지, ■로 정지.
import 'dart:async';
import 'dart:io';

import 'package:audio_service/audio_service.dart';
import 'package:flutter/material.dart';
import 'package:file_picker/file_picker.dart';
import 'package:http/http.dart' as http;
import 'package:just_audio/just_audio.dart';
import 'package:path_provider/path_provider.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'audio_handler.dart';

class PlayerScreen extends StatefulWidget {
  final String baseUrl;
  final String title;
  final String posKey; // 이어듣기 키 (jobId 또는 single file_id)
  final String downloadPath; // '/download/xxx' (baseUrl 뒤에 붙는 경로)
  final String fileName; // 저장 파일명
  const PlayerScreen({
    super.key,
    required this.baseUrl,
    required this.title,
    required this.posKey,
    required this.downloadPath,
    required this.fileName,
  });

  @override
  State<PlayerScreen> createState() => _PlayerScreenState();
}

class _PlayerScreenState extends State<PlayerScreen> {
  // Android以外 direct 재생용 공용 플레이어 (화면 닫아도 유지)
  static final _direct = AudioPlayer();

  String status = '준비 중...';
  double progress = 0; // 다운로드 진행률 0~1
  bool ready = false;
  bool _saving = false;
  double _speed = 1.0;
  Duration _dur = Duration.zero;
  Duration _lastPos = Duration.zero;
  Timer? _posTimer;
  StreamSubscription<Duration>? _posSub;

  bool get _svc => audioHandler != null;
  AudioPlayer get _player => _direct;

  @override
  void initState() {
    super.initState();
    _prepare();
  }

  @override
  void dispose() {
    // 재생은 유지 (백그라운드). 정지는 ■ 버튼.
    _posTimer?.cancel();
    _posSub?.cancel();
    super.dispose();
  }

  Future<Directory> _dir() => getApplicationDocumentsDirectory();

  Future<String> _localPath() async =>
      '${(await _dir()).path}/${widget.fileName}';

  Future<bool> _waitDone() async {
    // 장문 잡 완료 대기 (단문 single은 즉시 있음). 최대 3시간 폴링.
    if (!widget.downloadPath.startsWith('/download/')) return true;
    final jid = widget.downloadPath.split('/')[2];
    if (jid == 'single') return true;
    for (var i = 0; i < 5400; i++) {
      try {
        final r = await http.get(Uri.parse('${widget.baseUrl}/jobs/$jid'));
        if (r.statusCode == 200) {
          final m = r.body;
          if (m.contains('"status":"done"')) return true;
          if (m.contains('"status":"failed"')) {
            throw Exception('변환 실패');
          }
        }
      } catch (e) {
        if (e.toString().contains('변환 실패')) rethrow;
      }
      await Future.delayed(const Duration(seconds: 2));
      if (!mounted) return false;
    }
    throw Exception('대기 시간 초과');
  }

  Stream<Duration> get _positionStream =>
      _svc ? AudioService.position : _player.positionStream;

  Future<void> _setSource(String path) async {
    if (_svc) {
      await audioHandler!.playMediaItem(
        MediaItem(id: path, title: widget.title),
      );
    } else {
      await _player.setFilePath(path);
    }
  }

  Future<void> _doPlay() async {
    if (_svc) {
      await audioHandler!.play();
    } else {
      await _player.play();
    }
  }

  Future<void> _doPause() async {
    if (_svc) {
      await audioHandler!.pause();
    } else {
      await _player.pause();
    }
    await _savePos();
  }

  Future<void> _doStop() async {
    await _savePos();
    if (_svc) {
      await audioHandler!.stop();
    } else {
      await _player.stop();
    }
    if (mounted) setState(() => status = '정지됨');
  }

  Future<void> _doSeek(Duration d) async {
    if (_svc) {
      await audioHandler!.seek(d);
    } else {
      await _player.seek(d);
    }
  }

  Future<void> _doSpeed(double s) async {
    if (_svc) {
      await audioHandler!.setSpeed(s);
    } else {
      await _player.setSpeed(s);
    }
    if (mounted) setState(() => _speed = s);
  }

  Future<void> _prepare() async {
    try {
      final path = await _localPath();
      if (!File(path).existsSync()) {
        setState(() => status = '변환 대기 중...');
        final ok = await _waitDone();
        if (!ok || !mounted) return;
        setState(() => status = '다운로드 중... 0%');
        final req = http.Request(
            'GET', Uri.parse('${widget.baseUrl}${widget.downloadPath}'));
        final resp = await http.Client().send(req);
        if (resp.statusCode != 200) {
          throw Exception('다운로드 실패: ${resp.statusCode}');
        }
        final total = resp.contentLength ?? 0;
        var got = 0;
        final out = File(path).openWrite();
        await for (final chunk in resp.stream) {
          got += chunk.length;
          out.add(chunk);
          if (total > 0 && mounted) {
            setState(() {
              progress = got / total;
              status = '다운로드 중... ${(progress * 100).toStringAsFixed(0)}%';
            });
          }
        }
        await out.close();
      }
      final p = await SharedPreferences.getInstance();
      final resume = p.getInt('pos_${widget.posKey}') ?? 0;
      await _setSource(path);
      if (_svc) {
        _dur = await audioHandler!.mediaItem
                .map((m) => m?.duration)
                .firstWhere((d) => d != null && d > Duration.zero)
                .timeout(const Duration(seconds: 30), onTimeout: () => Duration.zero) ??
            Duration.zero;
      } else {
        _dur = _player.duration ?? Duration.zero;
      }
      if (resume > 0) {
        await _doSeek(Duration(seconds: resume));
      }
      if (!mounted) return;
      setState(() {
        ready = true;
        status = resume > 0
            ? '이어듣기: ${resume ~/ 60}분 ${resume % 60}초부터'
            : '재생 준비됨 — ▶를 누르세요 (화면을 닫아도 계속 재생)';
      });
      // 5초마다 위치 저장
      _posTimer =
          Timer.periodic(const Duration(seconds: 5), (_) => _savePos());
      _posSub = _positionStream.listen((d) => _lastPos = d);
    } catch (e) {
      if (mounted) setState(() => status = '오류: $e');
    }
  }

  /// 기기 공용 공간에 MP3 저장 (파일 앱·음악 앱에서 보임).
  /// Android: 저장 위치 선택기(MediaStore) → 권한 불필요.
  Future<void> _export() async {
    if (!ready) return;
    try {
      final path = await _localPath();
      final f = File(path);
      if (!f.existsSync()) {
        if (mounted) {
          ScaffoldMessenger.of(context)
              .showSnackBar(const SnackBar(content: Text('먼저 다운로드가 끝나야 합니다')));
        }
        return;
      }
      final bytes = await f.readAsBytes();
      final uri = await FilePicker.saveFile(
        fileName: widget.fileName,
        bytes: bytes,
        mimeType: 'audio/mpeg',
        dialogTitle: 'MP3 내보내기',
      );
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(
          content: Text(uri == null ? '취소됨' : '저장됨: $uri')));
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context)
            .showSnackBar(SnackBar(content: Text('내보내기 실패: $e')));
      }
    }
  }

  Future<void> _savePos() async {
    if (_saving || !ready) return;
    _saving = true;
    try {
      final p = await SharedPreferences.getInstance();
      await p.setInt('pos_${widget.posKey}', _lastPos.inSeconds);
    } finally {
      _saving = false;
    }
  }

  String _fmt(Duration? d) {
    d ??= Duration.zero;
    final h = d.inHours, m = d.inMinutes % 60, s = d.inSeconds % 60;
    return h > 0
        ? '$h:${m.toString().padLeft(2, '0')}:${s.toString().padLeft(2, '0')}'
        : '${m.toString().padLeft(2, '0')}:${s.toString().padLeft(2, '0')}';
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
          title: Text(widget.title,
              maxLines: 1, overflow: TextOverflow.ellipsis)),
      body: Padding(
        padding: const EdgeInsets.all(20),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            const Icon(Icons.audiotrack, size: 72),
            const SizedBox(height: 12),
            if (!ready)
              LinearProgressIndicator(
                  value: progress > 0 ? progress : null),
            const SizedBox(height: 8),
            Text(status, textAlign: TextAlign.center),
            const SizedBox(height: 16),
            if (ready)
              StreamBuilder<Duration>(
                stream: _positionStream,
                builder: (_, snap) {
                  final pos = snap.data ?? _lastPos;
                  final dur = _dur;
                  final max = dur.inMilliseconds > 0
                      ? dur.inMilliseconds.toDouble()
                      : 1.0;
                  final cur = pos.inMilliseconds
                      .clamp(0, dur.inMilliseconds)
                      .toDouble();
                  return Column(children: [
                    Slider(
                      value: cur,
                      max: max,
                      onChanged: (v) =>
                          _doSeek(Duration(milliseconds: v.toInt())),
                    ),
                    Text('${_fmt(pos)} / ${_fmt(dur)}'),
                  ]);
                },
              ),
            const SizedBox(height: 8),
            if (ready)
              Row(mainAxisAlignment: MainAxisAlignment.center, children: [
                IconButton(
                  tooltip: '10초 뒤로',
                  icon: const Icon(Icons.replay_10, size: 36),
                  onPressed: () =>
                      _doSeek(_lastPos - const Duration(seconds: 10)),
                ),
                const SizedBox(width: 8),
                StreamBuilder<bool>(
                  stream: _svc
                      ? audioHandler!.playbackState
                          .map((s) => s.playing)
                          .distinct()
                      : _player.playerStateStream
                          .map((s) => s.playing)
                          .distinct(),
                  builder: (_, snap) {
                    final playing = snap.data ?? false;
                    return IconButton(
                      tooltip: playing ? '일시정지' : '재생',
                      icon: Icon(
                          playing
                              ? Icons.pause_circle
                              : Icons.play_circle,
                          size: 64),
                      onPressed: () =>
                          playing ? _doPause() : _doPlay(),
                    );
                  },
                ),
                const SizedBox(width: 8),
                IconButton(
                  tooltip: '10초 앞으로',
                  icon: const Icon(Icons.forward_10, size: 36),
                  onPressed: () =>
                      _doSeek(_lastPos + const Duration(seconds: 10)),
                ),
                IconButton(
                  tooltip: '정지',
                  icon: const Icon(Icons.stop_circle, size: 36),
                  onPressed: _doStop,
                ),
              ]),
            if (ready)
              Row(mainAxisAlignment: MainAxisAlignment.center, children: [
                TextButton(
                  onPressed: () async {
                    const speeds = [1.0, 1.25, 1.5, 1.75, 2.0, 0.8];
                    final next = speeds.firstWhere(
                        (s) => s > _speed + 0.01,
                        orElse: () => speeds.first);
                    await _doSpeed(next);
                  },
                  child: Text('배속: ${_speed.toStringAsFixed(2)}x'),
                ),
                TextButton.icon(
                  onPressed: _export,
                  icon: const Icon(Icons.ios_share),
                  label: const Text('내보내기'),
                ),
              ]),
          ],
        ),
      ),
    );
  }
}
