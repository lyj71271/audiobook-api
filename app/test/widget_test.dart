import 'package:audiobook_app/main.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  testWidgets('앱이 4개 탭으로 시작한다', (tester) async {
    await tester.pumpWidget(const AudiobookApp());
    expect(find.text('오디오북'), findsOneWidget);
    expect(find.text('단문'), findsOneWidget);
    expect(find.text('장문'), findsOneWidget);
    expect(find.text('보관함'), findsOneWidget);
    expect(find.text('설정'), findsOneWidget);
  });
}
