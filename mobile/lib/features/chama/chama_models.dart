/// Mirrors app/schemas/chama.py's ChamaResponse.
///
/// monthly_contribution_ksh/total_savings_ksh come back as JSON *strings*
/// (Pydantic's default Decimal serialization, e.g. "500.00") - not numbers,
/// so they're parsed with double.parse rather than cast from num.
class Chama {
  final int id;
  final String chamaCode;
  final String name;
  final String? description;
  final String chamaType;
  final int memberCount;
  final double? monthlyContributionKsh;
  final double totalSavingsKsh;
  final String status;
  final bool isPublic;
  final bool isMember;
  final bool isPending;
  final bool isLeader;
  final String? mpesaPaybillNumber;

  Chama({
    required this.id,
    required this.chamaCode,
    required this.name,
    required this.description,
    required this.chamaType,
    required this.memberCount,
    required this.monthlyContributionKsh,
    required this.totalSavingsKsh,
    required this.status,
    required this.isPublic,
    required this.isMember,
    required this.isPending,
    required this.isLeader,
    required this.mpesaPaybillNumber,
  });

  factory Chama.fromJson(Map<String, dynamic> json) => Chama(
        id: json['id'] as int,
        chamaCode: json['chama_code'] as String,
        name: json['name'] as String,
        description: json['description'] as String?,
        chamaType: json['chama_type'] as String,
        memberCount: json['member_count'] as int,
        monthlyContributionKsh: json['monthly_contribution_ksh'] == null
            ? null
            : double.parse(json['monthly_contribution_ksh'] as String),
        totalSavingsKsh: double.parse(json['total_savings_ksh'] as String),
        status: json['status'] as String,
        isPublic: json['is_public'] as bool,
        isMember: json['is_member'] as bool,
        isPending: json['is_pending'] as bool? ?? false,
        isLeader: json['is_leader'] as bool? ?? false,
        mpesaPaybillNumber: json['mpesa_paybill_number'] as String?,
      );
}

/// Mirrors app/schemas/chama.py's ChamaMemberResponse.
class ChamaMember {
  final int userId;
  final String? fullName;
  final String? username;
  final String role;

  ChamaMember({required this.userId, required this.fullName, required this.username, required this.role});

  factory ChamaMember.fromJson(Map<String, dynamic> json) => ChamaMember(
        userId: json['user_id'] as int,
        fullName: json['full_name'] as String?,
        username: json['username'] as String?,
        role: json['role'] as String,
      );
}

/// Mirrors app/schemas/chama.py's ContributionResponse.
class Contribution {
  final int id;
  final String transactionId;
  final int userId;
  final double amountKsh;
  final String? paymentMethod;
  final String status;
  final String? notes;
  final DateTime? initiatedAt;

  Contribution({
    required this.id,
    required this.transactionId,
    required this.userId,
    required this.amountKsh,
    required this.paymentMethod,
    required this.status,
    required this.notes,
    required this.initiatedAt,
  });

  factory Contribution.fromJson(Map<String, dynamic> json) => Contribution(
        id: json['id'] as int,
        transactionId: json['transaction_id'] as String,
        userId: json['user_id'] as int,
        amountKsh: double.parse(json['amount_ksh'] as String),
        paymentMethod: json['payment_method'] as String?,
        status: json['status'] as String,
        notes: json['notes'] as String?,
        initiatedAt: json['initiated_at'] == null ? null : DateTime.parse(json['initiated_at'] as String),
      );
}
