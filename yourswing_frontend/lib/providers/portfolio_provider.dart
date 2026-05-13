import 'package:flutter/material.dart';
import '../models/portfolio_item.dart';
import '../services/portfolio_service.dart';
import '../services/api_service.dart';

class PortfolioProvider extends ChangeNotifier {
  final PortfolioService _portfolioService = PortfolioService();
  
  List<PortfolioItem> _holdings = [];
  Map<String, Map<String, double>> _livePrices = {};
  bool _isLoading = false;
  String? _error;

  List<PortfolioItem> get holdings => _holdings;
  Map<String, Map<String, double>> get livePrices => _livePrices;
  bool get isLoading => _isLoading;
  String? get error => _error;

  // Constructor
  PortfolioProvider() {
    loadPortfolio();
  }

  Future<void> loadPortfolio() async {
    _isLoading = true;
    _error = null;
    notifyListeners();

    try {
      // 1. Load holdings
      _holdings = await _portfolioService.getPortfolio();
      
      // 2. Fetch live prices if we have holdings
      if (_holdings.isNotEmpty) {
        final symbols = _holdings.map((e) {
          String sym = e.symbol.toUpperCase();
          return sym.contains('.') ? sym : '$sym.NS';
        }).toList();
        
        _livePrices = await apiService.fetchLatestPrices(symbols);
      } else {
        _livePrices = {};
      }
    } catch (e) {
      _error = e.toString();
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }

  Future<void> saveStock(PortfolioItem item) async {
    await _portfolioService.saveStock(item);
    await loadPortfolio(); // Refresh state
  }

  Future<void> deleteStock(String symbol) async {
    await _portfolioService.deleteStock(symbol);
    await loadPortfolio(); // Refresh state
  }

  // Calculate summary stats
  Map<String, double> getSummary() {
    double totalValue = 0;
    double totalInvestment = 0;
    double dailyChange = 0;
    
    for (var item in _holdings) {
      String symbol = item.symbol.toUpperCase();
      if (!symbol.contains('.')) symbol = '$symbol.NS';
      
      final stockData = _livePrices[symbol];
      double currentPrice = item.averagePrice;
      
      if (stockData != null && (stockData['price'] ?? 0) > 0) {
        currentPrice = stockData['price']!;
        dailyChange += (stockData['change'] ?? 0.0) * item.quantity;
      }
      
      totalValue += currentPrice * item.quantity;
      totalInvestment += item.averagePrice * item.quantity;
    }
    
    double pnl = totalValue - totalInvestment;
    double pnlPercent = totalInvestment > 0 ? (pnl / totalInvestment) * 100 : 0;
    
    return {
      'total': totalValue,        // For Dashboard
      'current': totalValue,      // For Portfolio
      'invested': totalInvestment,
      'pnl': pnl,
      'percent': pnlPercent,      // For Dashboard
      'pnlPct': pnlPercent,       // For Portfolio
      'dailyChange': dailyChange,
    };
  }
}
