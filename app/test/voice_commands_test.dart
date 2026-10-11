import 'package:audiobook_app/voice_commands.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  test('명령 분류', () {
    expect(parseVoiceCommand('합성해줘').action, VoiceAction.synth);
    expect(parseVoiceCommand('오디오로 만들어줘').action, VoiceAction.synth);
    expect(parseVoiceCommand('재생해줘').action, VoiceAction.play);
    expect(parseVoiceCommand('멈춰').action, VoiceAction.stop);
    expect(parseVoiceCommand('단문으로 이동').action, VoiceAction.goShort);
    expect(parseVoiceCommand('장문 탭 열어').action, VoiceAction.goLong);
    expect(parseVoiceCommand('보관함 보여줘').action, VoiceAction.goLibrary);
    expect(parseVoiceCommand('다 지워줘').action, VoiceAction.clear);
    expect(parseVoiceCommand('파일 가져와').action, VoiceAction.pickFile);
  });

  test('받아쓰기는 원문 유지', () {
    const s = '안녕하세요 오늘 날씨가 좋네요';
    final c = parseVoiceCommand(s);
    expect(c.action, VoiceAction.dictation);
    expect(c.text, s);
  });

  test('빈 입력은 받아쓰기 빈 문자열', () {
    final c = parseVoiceCommand('   ');
    expect(c.action, VoiceAction.dictation);
    expect(c.text, isEmpty);
  });
}
