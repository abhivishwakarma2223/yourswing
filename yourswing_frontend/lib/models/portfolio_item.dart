class PortfolioItem {
  final String symbol;
  final String name;
  final double quantity;
  final double averagePrice;

  PortfolioItem({
    required this.symbol,
    required this.name,
    required this.quantity,
    required this.averagePrice,
  });

  Map<String, dynamic> toMap() {
    return {
      'symbol': symbol,
      'name': name,
      'quantity': quantity,
      'averagePrice': averagePrice,
    };
  }

  factory PortfolioItem.fromMap(Map<String, dynamic> map) {
    return PortfolioItem(
      symbol: map['symbol'] ?? '',
      name: map['name'] ?? '',
      quantity: (map['quantity'] ?? 0.0).toDouble(),
      averagePrice: (map['averagePrice'] ?? 0.0).toDouble(),
    );
  }
}
