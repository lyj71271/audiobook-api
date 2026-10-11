// 서버 주소 런타임 설정 (mobile-deploy 스킬 3.1).
// 컴파일 타임 String.fromEnvironment 금지 — 설정 화면에서 변경 즉시 반영.
import 'package:flutter/foundation.dart';
import 'package:shared_preferences/shared_preferences.dart';

const _key = 'api_base';

String defaultBase() {
  // Android 실기기/에뮬레이터는 PC 루프백에 직접 닿지 않음.
  // 에뮬레이터=10.0.2.2, 실기기=설정에서 PC LAN IP 입력.
  if (defaultTargetPlatform == TargetPlatform.android) {
    return 'http://10.0.2.2:8002';
  }
  return 'http://127.0.0.1:8002';
}

/// 전역 서버 주소. 설정 화면에서 setBase 호출 시 모든 화면에 즉시 반영.
final apiBase = ValueNotifier<String>(defaultBase());

Future<void> initApiBase() async {
  final p = await SharedPreferences.getInstance();
  final saved = p.getString(_key);
  if (saved != null && saved.trim().isNotEmpty) {
    apiBase.value = saved.trim();
  }
}

Future<void> setApiBase(String url) async {
  final v = url.trim().replaceAll(RegExp(r'/+$'), '');
  final p = await SharedPreferences.getInstance();
  await p.setString(_key, v);
  apiBase.value = v;
}
