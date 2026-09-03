// Guards against drift from app/schemas/chama.py's response shapes - matches
// actual live responses captured while building app/api/chamas.py (see
// mobile/CHANGELOG.md 2026-09-03). The Decimal fields (monthly_contribution_ksh,
// total_savings_ksh, amount_ksh) are the reason these are worth testing: the
// backend serializes them as JSON *strings* ("500.00"), not numbers - an easy
// thing to get wrong with a silent runtime crash instead of a compile error.

import 'package:flutter_test/flutter_test.dart';
import 'package:agropulse_mobile/features/chama/chama_models.dart';

void main() {
  test('Chama.fromJson parses a real backend response, including string-typed Decimal fields', () {
    final chama = Chama.fromJson({
      'id': 28,
      'chama_code': 'CHM-31FCA8EB',
      'name': 'Nakuru Women Farmers Chama',
      'description': 'Monthly savings group for horticulture inputs',
      'chama_type': 'savings',
      'member_count': 2,
      'monthly_contribution_ksh': '500.00',
      'total_savings_ksh': '500.00',
      'status': 'active',
      'is_public': true,
      'is_member': true,
      'created_at': '2026-09-03T07:17:31.858188Z',
    });

    expect(chama.name, 'Nakuru Women Farmers Chama');
    expect(chama.memberCount, 2);
    expect(chama.monthlyContributionKsh, 500.0);
    expect(chama.totalSavingsKsh, 500.0);
    expect(chama.isMember, isTrue);
  });

  test('Chama.fromJson parses is_pending/is_leader/mpesa_paybill_number (added for the join-request flow)', () {
    final leader = Chama.fromJson({
      'id': 29, 'chama_code': 'CHM-DCED095D', 'name': 'Approval Test Chama', 'description': null,
      'chama_type': 'savings', 'member_count': 2, 'monthly_contribution_ksh': null,
      'total_savings_ksh': '0.00', 'status': 'active', 'is_public': true, 'is_member': true,
      'is_pending': false, 'is_leader': true, 'mpesa_paybill_number': '400200',
      'created_at': '2026-09-03T08:49:02.645346Z',
    });
    expect(leader.isLeader, isTrue);
    expect(leader.mpesaPaybillNumber, '400200');

    final pendingRequester = Chama.fromJson({
      'id': 29, 'chama_code': 'CHM-DCED095D', 'name': 'Approval Test Chama', 'description': null,
      'chama_type': 'savings', 'member_count': 2, 'monthly_contribution_ksh': null,
      'total_savings_ksh': '0.00', 'status': 'active', 'is_public': true, 'is_member': false,
      'is_pending': true, 'is_leader': false, 'mpesa_paybill_number': null,
      'created_at': '2026-09-03T08:49:02.645346Z',
    });
    expect(pendingRequester.isPending, isTrue);
    expect(pendingRequester.isMember, isFalse);
    expect(pendingRequester.mpesaPaybillNumber, isNull, reason: 'hidden from non-members by the backend');
  });

  test('Chama.fromJson handles a null monthly_contribution_ksh', () {
    final chama = Chama.fromJson({
      'id': 1, 'chama_code': 'CHM-X', 'name': 'No fixed amount', 'description': null,
      'chama_type': 'welfare', 'member_count': 1, 'monthly_contribution_ksh': null,
      'total_savings_ksh': '0.00', 'status': 'active', 'is_public': false, 'is_member': false,
      'created_at': null,
    });

    expect(chama.monthlyContributionKsh, isNull);
    expect(chama.totalSavingsKsh, 0.0);
  });

  test('ChamaMember.fromJson parses a real member row', () {
    final member = ChamaMember.fromJson({
      'user_id': 514, 'full_name': 'Farm Tester', 'username': 'farmtester1',
      'role': 'chairperson', 'joined_at': '2026-09-03T07:17:31.858188Z',
    });

    expect(member.fullName, 'Farm Tester');
    expect(member.role, 'chairperson');
  });

  test('Contribution.fromJson parses a real contribution response', () {
    final contribution = Contribution.fromJson({
      'id': 451, 'transaction_id': 'TXN-cb26a40c4bef', 'user_id': 515,
      'amount_ksh': '500.00', 'payment_method': 'mpesa', 'status': 'completed',
      'notes': 'September contribution', 'initiated_at': '2026-09-03T07:18:40.510514Z',
    });

    expect(contribution.amountKsh, 500.0);
    expect(contribution.paymentMethod, 'mpesa');
    expect(contribution.status, 'completed');
    expect(contribution.initiatedAt, isNotNull);
  });
}
