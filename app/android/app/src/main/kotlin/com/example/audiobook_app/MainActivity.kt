package com.example.audiobook_app

import com.ryanheise.audioservice.AudioServiceActivity

// audio_service 백그라운드 재생 필수: AudioServiceActivity를 상속해야
// AudioService.init이 엔진에 붙는다 (일반 FlutterActivity면 시작 먹통).
class MainActivity : AudioServiceActivity()
