/// Mirrors app/api/farms.py's FarmListResponse / PaginatedFarmsResponse.
class Farm {
  final int id;
  final String uuid;
  final String name;
  final String county;
  final double sizeAcres;
  final String? primaryCrop;
  final double latitude;
  final double longitude;
  final bool isActive;

  Farm({
    required this.id,
    required this.uuid,
    required this.name,
    required this.county,
    required this.sizeAcres,
    required this.primaryCrop,
    required this.latitude,
    required this.longitude,
    required this.isActive,
  });

  factory Farm.fromJson(Map<String, dynamic> json) => Farm(
        id: json['id'] as int,
        uuid: json['uuid'] as String,
        name: json['name'] as String,
        county: json['county'] as String,
        sizeAcres: (json['size_acres'] as num).toDouble(),
        primaryCrop: json['primary_crop'] as String?,
        latitude: (json['latitude'] as num).toDouble(),
        longitude: (json['longitude'] as num).toDouble(),
        isActive: json['is_active'] as bool,
      );
}

class PaginatedFarms {
  final List<Farm> items;
  final int total;
  final int page;
  final int pages;

  PaginatedFarms({required this.items, required this.total, required this.page, required this.pages});

  factory PaginatedFarms.fromJson(Map<String, dynamic> json) => PaginatedFarms(
        items: (json['items'] as List).map((e) => Farm.fromJson(e as Map<String, dynamic>)).toList(),
        total: json['total'] as int,
        page: json['page'] as int,
        pages: json['pages'] as int,
      );
}
