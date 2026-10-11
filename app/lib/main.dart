// Audiobook MVP — 단문 즉시변환 + 장문 큐 + 이어듣기
// 백엔드: http://localhost:8000 (데스크톱), Android 에뮬레이터는 10.0.2.2:8000
// 사용 API: POST /synth, POST /convert/file (multipart), GET /jobs/{id}
import 'dart:async';
import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'dart:convert';
import 'package:just_audio/just_audio.dart';
import 'package:file_picker/file_picker.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:speech_to_text/speech_to_text.dart';
import 'audio_handler.dart';
import 'server.dart';
import 'player.dart';
import 'voice_commands.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  await initApiBase();
  // 백그라운드 재생은 Android만 (Windows direct 재생)
  if (defaultTargetPlatform == TargetPlatform.android) {
    await initAudioService();
  }
  runApp(const AudiobookApp());
}

class AudiobookApp extends StatelessWidget {
  const AudiobookApp({super.key});
  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: '오디오북',
      theme: ThemeData(useMaterial3: true, colorSchemeSeed: Colors.indigo),
      home: const HomeTabs(),
    );
  }
}

class HomeTabs extends StatefulWidget {
  const HomeTabs({super.key});
  @override
  State<HomeTabs> createState() => _HomeTabsState();
}

class _HomeTabsState extends State<HomeTabs> {
  int idx = 0;
  final _stt = SpeechToText();
  bool _listening = false;
  String _heard = '';

  @override
  void dispose() {
    _stt.stop();
    super.dispose();
  }

  Future<void> _toggleGlobalVoice() async {    if (_listening) {
      await _stt.stop();
      setState(() => _listening = false);
      return;
    }
    final ok = await _stt.initialize();
    if (!ok) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('음성인식을 쓸 수 없습니다. 데스크톱은 Win+H 받아쓰기를 쓰세요.')));
      }
      return;
    }
    setState(() => _listening = true);
    await _stt.listen(
      listenOptions: SpeechListenOptions(localeId: 'ko_KR'),
      onResult: (r) {
        _heard = r.recognizedWords;
        if (!r.finalResult) return;
        final cmd = parseVoiceCommand(_heard);
        setState(() => _listening = false);
        switch (cmd.action) {
          case VoiceAction.goShort:
            setState(() => idx = 0);
            break;
          case VoiceAction.goLong:
            setState(() => idx = 1);
            break;
          case VoiceAction.goLibrary:
            setState(() => idx = 2);
            break;
          case VoiceAction.pickFile:
            setState(() => idx = 1);
            if (mounted) {
              ScaffoldMessenger.of(context).showSnackBar(
                const SnackBar(content: Text('장문 탭에서 “파일 가져오기”를 누르세요')));
            }
            break;
          default:
            if (mounted) {
              ScaffoldMessenger.of(context).showSnackBar(
                SnackBar(content: Text('전역 명령이 아님: "$_heard" — 단문 탭 🎤에서 받아쓰기 하세요')));
            }
        }
      },
    );
  }

  @override
  Widget build(BuildContext context) {
    return ValueListenableBuilder<String>(
      valueListenable: apiBase,
      builder: (_, base, __) {
        final pages = [
          const ShortTab(),
          const LongTab(),
          const LibraryTab(),
          const SettingsTab(),
        ];
        return Scaffold(
          appBar: AppBar(
            title: const Text('오디오북'),
            actions: [
              IconButton(
                tooltip: _listening ? '음성 듣는 중 (탭 명령)' : '음성 명령 (단문/장문/보관함)',
                icon: Icon(_listening ? Icons.mic : Icons.mic_none),
                onPressed: _toggleGlobalVoice,
              ),
            ],
          ),
          body: pages[idx],
          bottomNavigationBar: NavigationBar(
            selectedIndex: idx,
            onDestinationSelected: (i) => setState(() => idx = i),
            destinations: const [
              NavigationDestination(icon: Icon(Icons.bolt), label: '단문'),
              NavigationDestination(icon: Icon(Icons.book), label: '장문'),
              NavigationDestination(icon: Icon(Icons.library_music), label: '보관함'),
              NavigationDestination(icon: Icon(Icons.settings), label: '설정'),
            ],
          ),
        );
      },
    );
  }
}

class ShortTab extends StatefulWidget {
  const ShortTab({super.key});
  @override
  State<ShortTab> createState() => _ShortTabState();
}

class _ShortTabState extends State<ShortTab> {
  final ctrl = TextEditingController();
  String status = '';
  String fileId = '';
  final player = AudioPlayer();
  final _stt = SpeechToText();
  bool _listening = false;

  // 2000자 이하는 동기 /synth, 초과는 잡(/synth/job) → 플레이어가 폴링.
  // 웹 배포의 프록시 타임아웃을 피하기 위함.
  static const _jobThreshold = 2000;

  Future<void> synthAndPlay() async {
    if (ctrl.text.trim().isEmpty) { setState(() => status = '텍스트를 입력하세요'); return; }
    if (ctrl.text.length > _jobThreshold) {
      await _synthJob();
      return;
    }
    setState(() { status = '합성 중...'; fileId = ''; });
    // 글자수 비례 타임아웃 (100자→약 40초). 무한 대기 방지.
    final limit = Duration(seconds: 30 + (ctrl.text.length ~/ 10));
    try {
      final r = await http.post(Uri.parse('${apiBase.value}/synth'),
          headers: {'Content-Type': 'application/json'},
          body: jsonEncode({'text': ctrl.text, 'out': 'out/single.mp3'})).timeout(limit);
      if (r.statusCode != 200) { setState(() => status = '실패: ${r.body}'); return; }
      final m = jsonDecode(r.body);
      setState(() {
        fileId = (m['file_id'] ?? '') as String;
        status = '완료 (${m['chars']}자) — 아래 듣기로 재생';
      });
    } on TimeoutException {
      setState(() => status = '시간 초과 — 서버 주소·Wi-Fi 확인 후 다시 시도');
    } catch (e) {
      setState(() => status = '오류: $e (설정 탭에서 서버 주소 확인)');
    }
  }

  Future<void> _synthJob() async {
    setState(() { status = '잡 등록 중...'; fileId = ''; });
    try {
      final r = await http.post(Uri.parse('${apiBase.value}/synth/job'),
          headers: {'Content-Type': 'application/json'},
          body: jsonEncode({'text': ctrl.text, 'title': '단문합성'})).timeout(const Duration(seconds: 30));
      if (r.statusCode != 200) { setState(() => status = '실패: ${r.body}'); return; }
      final jid = jsonDecode(r.body)['job_id'] as String;
      if (!mounted) return;
      setState(() => status = '장문 잡 시작 — 플레이어에서 진행 확인');
      Navigator.of(context).push(MaterialPageRoute(
        builder: (_) => PlayerScreen(
          baseUrl: apiBase.value,
          title: '단문 합성 결과',
          posKey: jid,
          downloadPath: '/download/$jid',
          fileName: '${jid}_단문합성.mp3',
        ),
      ));
    } on TimeoutException {
      setState(() => status = '시간 초과 — 서버 주소·Wi-Fi 확인 후 다시 시도');
    } catch (e) {
      setState(() => status = '오류: $e (설정 탭에서 서버 주소 확인)');
    }
  }

  void _openPlayer() {
    if (fileId.isEmpty) return;
    Navigator.of(context).push(MaterialPageRoute(
      builder: (_) => PlayerScreen(
        baseUrl: apiBase.value,
        title: '단문 합성 결과',
        posKey: 'single_$fileId',
        downloadPath: '/download/single/$fileId',
        fileName: 'single_$fileId.mp3',
      ),
    ));
  }

  @override
  void dispose() { _stt.stop(); player.dispose(); ctrl.dispose(); super.dispose(); }

  Future<void> _toggleVoice() async {
    if (_listening) {
      await _stt.stop();
      setState(() => _listening = false);
      return;
    }
    final ok = await _stt.initialize();
    if (!ok) {
      setState(() => status = '음성인식 불가 — 데스크톱은 Win+H 받아쓰기 사용');
      return;
    }
    setState(() {
      _listening = true;
      status = '듣는 중... “합성해줘/지워줘”라고 말하거나 문장을 말하세요';
    });
    await _stt.listen(
      listenOptions: SpeechListenOptions(localeId: 'ko_KR'),
      onResult: (r) {
        if (!r.finalResult) {
          setState(() => status = '인식 중: ${r.recognizedWords}');
          return;
        }
        final heard = r.recognizedWords;
        final cmd = parseVoiceCommand(heard);
        setState(() => _listening = false);
        switch (cmd.action) {
          case VoiceAction.clear:
            ctrl.clear();
            setState(() => status = '지움');
            break;
          case VoiceAction.synth:
            // "합성해줘" 앞에 받아쓴 문장이 있으면 유지하고 합성
            setState(() => status = '음성 명령 인식: 합성 — "$heard"');
            synthAndPlay();
            break;
          case VoiceAction.play:
          case VoiceAction.stop:
            setState(() => status = '“${cmd.action == VoiceAction.play ? '재생' : '정지'}” 명령 인식 — 단문 탭은 합성 후 백엔드 mp3 저장 방식이라 로컬 미리듣기는 추후 지원');
            break;
          case VoiceAction.goShort:
          case VoiceAction.goLong:
          case VoiceAction.goLibrary:
          case VoiceAction.pickFile:
            setState(() => status = '탭 이동/파일 명령은 상단 🎤(전역 마이크)를 쓰세요 — "$heard"');
            break;
          case VoiceAction.dictation:
            final cur = ctrl.text;
            final sep = cur.isEmpty || cur.endsWith('\n') || cur.endsWith(' ') ? '' : ' ';
            ctrl.text = '$cur$sep${cmd.text}';
            setState(() => status = '받아쓰기: "${cmd.text}"');
            break;
        }
      },
    );
  }

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.all(16),
      child: Column(children: [
        Expanded(child: TextField(controller: ctrl, maxLines: null, expands: true,
            decoration: const InputDecoration(hintText: '여기에 텍스트 입력', border: OutlineInputBorder()))),
        const SizedBox(height: 8),
        Row(children: [
          ElevatedButton.icon(onPressed: synthAndPlay, icon: const Icon(Icons.play_arrow), label: const Text('합성')),
          if (fileId.isNotEmpty)
            TextButton.icon(onPressed: _openPlayer, icon: const Icon(Icons.headphones), label: const Text('듣기')),
          IconButton(
            tooltip: _listening ? '듣는 중 — 누르면 중지' : '🎤 말로 입력 / “합성해줘”',
            icon: Icon(_listening ? Icons.mic : Icons.mic_none),
            color: _listening ? Colors.red : null,
            onPressed: _toggleVoice,
          ),
          Expanded(child: Text(status)),
        ]),
      ]),
    );
  }
}

class _JobState {
  final String jobId;
  final String name;
  double progress = 0;
  String status = 'queued';
  String out = '';
  String error = '';
  _JobState(this.jobId, this.name);
}

// 서버 상태값 → 한글 표시 (영문판 만들 때 여기만 교체)
const _statusKo = {
  'created': '생성됨',
  'queued': '대기 중',
  'extracting': '추출 중',
  'synthesizing': '합성 중',
  'merging': '합치기 중',
  'done': '완료',
  'failed': '실패',
};

class LongTab extends StatefulWidget {
  const LongTab({super.key});
  @override
  State<LongTab> createState() => _LongTabState();
}

class _LongTabState extends State<LongTab> {
  final List<_JobState> jobs = [];
  Timer? poller;

  @override
  void initState() {
    super.initState();
    poller = Timer.periodic(const Duration(seconds: 2), (_) => _pollAll());
  }

  @override
  void dispose() { poller?.cancel(); super.dispose(); }

  Future<void> _pickAndUpload() async {
    final files = await FilePicker.pickFiles(
      type: FileType.custom,
      allowedExtensions: ['txt', 'md', 'pdf', 'epub', 'docx'],
    );
    if (files.isEmpty) return;
    final f = files.first;
    final bytes = await f.readAsBytes();
    if (bytes.isEmpty) return;
    final req = http.MultipartRequest('POST', Uri.parse('${apiBase.value}/convert/file?title=${Uri.encodeComponent(f.name.split('.').first)}'));
    req.files.add(http.MultipartFile.fromBytes('file', bytes, filename: f.name));
    final resp = await req.send();
    final body = await resp.stream.bytesToString();
    if (resp.statusCode != 200) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('업로드 실패: $body')));
      return;
    }
    final jobId = jsonDecode(body)['job_id'] as String;
    setState(() => jobs.insert(0, _JobState(jobId, f.name)));
    _saveToLibrary(f.name, jobId);
  }

  Future<void> _pollAll() async {
    for (final j in jobs) {
      if (j.status == 'done' || j.status == 'failed') continue;
      try {
        final r = await http.get(Uri.parse('${apiBase.value}/jobs/${j.jobId}')).timeout(const Duration(seconds: 15));
        if (r.statusCode != 200) continue;
        final m = jsonDecode(r.body);
        setState(() {
          j.status = m['status'] ?? '';
          j.progress = (m['progress'] ?? 0).toDouble();
          j.out = m['out'] ?? '';
          j.error = m['error'] ?? '';
        });
      } catch (_) {}
    }
  }

  Future<void> _saveToLibrary(String name, String jobId) async {
    final p = await SharedPreferences.getInstance();
    final list = p.getStringList('library') ?? [];
    list.insert(0, '$name|$jobId|${DateTime.now().toIso8601String()}');
    await p.setStringList('library', list.take(50).toList());
  }

  String _sub(_JobState j) {
    if (j.status == 'done') return '완료 · ${j.name.split('.').first}.mp3';
    if (j.status == 'failed') return '실패 · ${j.error}';
    return '${_statusKo[j.status] ?? j.status} ${(j.progress * 100).toStringAsFixed(0)}%';
  }

  void _openPlayer(_JobState j) {
    Navigator.of(context).push(MaterialPageRoute(
      builder: (_) => PlayerScreen(
        baseUrl: apiBase.value,
        title: j.name,
        posKey: j.jobId,
        downloadPath: '/download/${j.jobId}',
        fileName: '${j.jobId}_${j.name.split('.').first}.mp3',
      ),
    ));
  }

  @override
  Widget build(BuildContext context) {
    return Column(children: [
      Padding(
        padding: const EdgeInsets.all(12),
        child: Row(children: [
          ElevatedButton.icon(onPressed: _pickAndUpload, icon: const Icon(Icons.upload_file), label: const Text('파일 가져오기 (txt/pdf/epub/docx)')),
        ]),
      ),
      Expanded(
        child: jobs.isEmpty
            ? const Center(child: Text('아직 변환 작업이 없습니다.\n파일을 가져오면 여기에 진행률이 표시됩니다.'))
            : ListView.builder(
                itemCount: jobs.length,
                itemBuilder: (_, i) {
                  final j = jobs[i];
                  return Card(
                    margin: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                    child: ListTile(
                      title: Text(j.name, maxLines: 1, overflow: TextOverflow.ellipsis),
                      subtitle: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                        LinearProgressIndicator(value: j.status == 'done' ? 1 : j.progress),
                        const SizedBox(height: 4),
                        Text(_sub(j),
                            maxLines: 2, overflow: TextOverflow.ellipsis),
                      ]),
                      trailing: j.status == 'done'
                          ? const Icon(Icons.play_arrow)
                          : j.status == 'failed'
                              ? IconButton(icon: const Icon(Icons.refresh), onPressed: () {/* 재시도: 파일 재업로드 */})
                              : null,
                      onTap: j.status == 'done' ? () => _openPlayer(j) : null,
                    ),
                  );
                },
              ),
      ),
    ]);
  }
}

class LibraryTab extends StatefulWidget {
  const LibraryTab({super.key});
  @override
  State<LibraryTab> createState() => _LibraryTabState();
}

class _LibraryTabState extends State<LibraryTab> {
  List<String> items = [];
  Map<String, int> positions = {}; // jobId -> seconds (이어듣기)

  @override
  void initState() { super.initState(); _load(); }

  Future<void> _load() async {
    final p = await SharedPreferences.getInstance();
    setState(() {
      items = p.getStringList('library') ?? [];
      for (final k in p.getKeys().where((k) => k.startsWith('pos_'))) {
        positions[k.substring(4)] = p.getInt(k) ?? 0;
      }
    });
  }

  Future<void> _savePosition(String jobId, int secs) async {
    final p = await SharedPreferences.getInstance();
    await p.setInt('pos_$jobId', secs);
    _load();
  }

  Future<void> _openItem(String name, String jobId) async {
    if (jobId.isEmpty) return;
    try {
      final r = await http.get(Uri.parse('${apiBase.value}/jobs/$jobId'));
      if (r.statusCode != 200) {
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(content: Text('서버에 작업 없음 (재시작 시 소실) — 장문 탭에서 다시 변환하세요')));
        }
        return;
      }
      final m = jsonDecode(r.body);
      if ((m['status'] ?? '') != 'done') {
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(content: Text('아직 변환 중: ${_statusKo[m['status']] ?? m['status']}')));
        }
        return;
      }
    } catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('오류: $e')));
      return;
    }
    if (!mounted) return;
    Navigator.of(context).push(MaterialPageRoute(
      builder: (_) => PlayerScreen(
        baseUrl: apiBase.value,
        title: name,
        posKey: jobId,
        downloadPath: '/download/$jobId',
        fileName: '${jobId}_${name.split('.').first}.mp3',
      ),
    ));
  }

  @override
  Widget build(BuildContext context) {
    if (items.isEmpty) return const Center(child: Text('보관함이 비어 있습니다. 장문 탭에서 변환하면 여기에 쌓입니다.'));
    return ListView.builder(
      itemCount: items.length,
      itemBuilder: (_, i) {
        final parts = items[i].split('|');
        final name = parts[0];
        final jobId = parts.length > 1 ? parts[1] : '';
        final pos = positions[jobId] ?? 0;
        return ListTile(
          leading: const Icon(Icons.audiotrack),
          title: Text(name, maxLines: 1, overflow: TextOverflow.ellipsis),
          subtitle: Text(pos > 0 ? '이어듣기: ${pos ~/ 60}분 ${pos % 60}초부터' : '새로 듣기'),
          onTap: () => _openItem(name, jobId),
          trailing: PopupMenuButton<String>(
            onSelected: (v) {
              if (v == 'reset') _savePosition(jobId, 0);
              if (v == 'demo30') _savePosition(jobId, 1800); // 데모: 30분 위치 저장
            },
            itemBuilder: (_) => const [
              PopupMenuItem(value: 'demo30', child: Text('30분 위치 저장 (데모)')),
              PopupMenuItem(value: 'reset', child: Text('위치 초기화')),
            ],
          ),
        );
      },
    );
  }
}

class SettingsTab extends StatefulWidget {
  const SettingsTab({super.key});
  @override
  State<SettingsTab> createState() => _SettingsTabState();
}

class _SettingsTabState extends State<SettingsTab> {
  final ctrl = TextEditingController();
  String msg = '';

  @override
  void initState() {
    super.initState();
    ctrl.text = apiBase.value;
  }

  @override
  void dispose() {
    ctrl.dispose();
    super.dispose();
  }

  Future<void> _checkAndSave() async {
    final url = ctrl.text.trim().replaceAll(RegExp(r'/+$'), '');
    if (url.isEmpty) {
      setState(() => msg = '주소를 입력하세요 (예: http://192.168.0.22:8002)');
      return;
    }
    setState(() => msg = '연결 확인 중...');
    try {
      final r = await http.get(Uri.parse('$url/health')).timeout(const Duration(seconds: 8));
      if (r.statusCode == 200 && r.body.contains('"ok":true')) {
        await setApiBase(url);
        if (mounted) setState(() => msg = '연결됨 — 저장됨: $url');
      } else {
        if (mounted) setState(() => msg = '응답 이상: ${r.statusCode} — 백엔드가 맞나요?');
      }
    } catch (e) {
      if (mounted) setState(() => msg = '연결 실패 — 같은 Wi-Fi? 방화벽? 주소 확인');
    }
  }

  @override
  Widget build(BuildContext context) {
    return ListView(padding: const EdgeInsets.all(20), children: [
      const Text('서버 주소', style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
      const SizedBox(height: 8),
      const Text('PC 백엔드 주소. 실기기면 PC의 LAN IP를 입력하세요.\n'
          '예: http://192.168.0.22:8002 (PC에서 ipconfig로 확인)'),
      const SizedBox(height: 12),
      TextField(
        controller: ctrl,
        keyboardType: TextInputType.url,
        decoration: const InputDecoration(
          border: OutlineInputBorder(),
          hintText: 'http://192.168.0.22:8002',
        ),
      ),
      const SizedBox(height: 12),
      ElevatedButton.icon(
        onPressed: _checkAndSave,
        icon: const Icon(Icons.link),
        label: const Text('연결 확인 후 저장'),
      ),
      const SizedBox(height: 8),
      Text(msg),
      const Divider(height: 32),
      Text('현재: ${apiBase.value}'),
    ]);
  }
}
