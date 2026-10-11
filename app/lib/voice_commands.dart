// 음성 명령 파서 — 순수 Dart, Flutter/speech_to_text 의존 없음.
// 규칙: 명령 키워드가 포함되면 액션, 그 외는 받아쓰기.
// 스킬 정책: 무료/로컬 우선 → OS 기본 STT(speech_to_text) 전제.

enum VoiceAction {
  synth, // "합성해줘", "변환해줘", "만들어줘"
  play, // "재생", "틀어줘", "들려줘"
  stop, // "정지", "멈춰", "일시정지"
  goShort, // "단문 (탭)"
  goLong, // "장문 (탭)"
  goLibrary, // "보관함", "라이브러리"
  clear, // "지워", "삭제", "비워"
  pickFile, // "파일 가져와", "파일 열어"
  dictation, // 일반 받아쓰기
}

class VoiceCommand {
  final VoiceAction action;
  final String text; // 받아쓰기일 때 인식된 원문
  const VoiceCommand(this.action, [this.text = '']);
}

/// 인식 문장을 명령으로 분류. 앞뒤 공백 제거 후 키워드 포함 여부로 판단.
/// 명령 우선순위: 이동 > 파일 > 지우기 > 합성/재생/정지 > 받아쓰기
VoiceCommand parseVoiceCommand(String input) {
  final s = input.trim().replaceAll(RegExp(r'\s+'), ' ');
  if (s.isEmpty) return const VoiceCommand(VoiceAction.dictation, '');

  bool has(List<String> keys) => keys.any((k) => s.contains(k));

  // 탭 이동 (가장 먼저 — "장문으로 이동" 같은 발화와 합성 키워드 충돌 방지)
  if (has(['단문']) && has(['이동', '가줘', '가져가', '열어', '보여', '탭', '화면'])) {
    return const VoiceCommand(VoiceAction.goShort);
  }
  if (has(['장문']) && has(['이동', '가줘', '가져가', '열어', '보여', '탭', '화면'])) {
    return const VoiceCommand(VoiceAction.goLong);
  }
  if (has(['보관함', '라이브러리', '보관 함'])) {
    return const VoiceCommand(VoiceAction.goLibrary);
  }
  // 단독 "단문/장문" 한 단어도 이동으로 처리
  if (s == '단문') return const VoiceCommand(VoiceAction.goShort);
  if (s == '장문') return const VoiceCommand(VoiceAction.goLong);

  // 파일 가져오기
  if (has(['파일']) && has(['가져와', '가져 와', '열어', '선택', '업로드', '불러와'])) {
    return const VoiceCommand(VoiceAction.pickFile);
  }

  // 지우기
  if (has(['지워', '삭제', '비워', '다 지워'])) {
    return const VoiceCommand(VoiceAction.clear);
  }

  // 합성 / 재생 / 정지
  if (has(['합성', '변환해', '오디오로', '만들어', '읽어줘'])) {
    return const VoiceCommand(VoiceAction.synth);
  }
  if (has(['재생', '틀어', '들려', '플레이'])) {
    return const VoiceCommand(VoiceAction.play);
  }
  if (has(['정지', '멈춰', '일시정지', '스톱', '그만'])) {
    return const VoiceCommand(VoiceAction.stop);
  }

  return VoiceCommand(VoiceAction.dictation, s);
}
