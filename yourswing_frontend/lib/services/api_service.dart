import 'dart:convert';
import 'package:http/http.dart' as http;

class ApiService {
  // Production Railway URL
  final String baseUrl = 'https://yourswing-production.up.railway.app/api';

  Future<Map<String, dynamic>?> fetchStockAnalysis(String symbol) async {
    // Normalize: ensure it's uppercase
    String normalized = symbol.trim().toUpperCase();
    
    // Only add .NS if it doesn't have a dot and is likely an Indian symbol
    // (e.g. RELIANCE -> RELIANCE.NS, but AAPL remains AAPL if you want US)
    if (!normalized.contains('.')) {
      // Common heuristic for NSE: if it's 5-10 chars and no dot, it's likely NSE
      normalized = '$normalized.NS';
    }
    
    try {
      final response = await http.get(Uri.parse('$baseUrl/analysis/$normalized'));
      
      if (response.statusCode == 200) {
        return json.decode(response.body);
      }
      return null;
    } catch (e) {
      print('Error fetching analysis: $e');
      return null;
    }
  }

  Future<List<Map<String, dynamic>>> getTrendingStocks() async {
    try {
      final response = await http.get(Uri.parse('$baseUrl/trending'));
      
      if (response.statusCode == 200) {
        List<dynamic> data = json.decode(response.body);
        return List<Map<String, dynamic>>.from(data);
      }
      return [];
    } catch (e) {
      print('Error fetching trending stocks: $e');
      return [];
    }
  }

  // Fetch multiple prices and changes in parallel
  Future<Map<String, Map<String, double>>> fetchLatestPrices(List<String> symbols) async {
    if (symbols.isEmpty) return {};
    
    try {
      final response = await http.post(
        Uri.parse('$baseUrl/prices/batch'),
        headers: {'Content-Type': 'application/json'},
        body: json.encode(symbols),
      );
      
      if (response.statusCode == 200) {
        final Map<String, dynamic> data = json.decode(response.body);
        Map<String, Map<String, double>> results = {};
        data.forEach((key, value) {
          if (value != null && value is Map) {
            results[key] = {
              'price': (value['price'] ?? 0.0).toDouble(),
              'change': (value['change'] ?? 0.0).toDouble(),
              'changePercent': (value['changePercent'] ?? 0.0).toDouble(),
            };
          } else {
            results[key] = {'price': 0.0, 'change': 0.0, 'changePercent': 0.0};
          }
        });
        return results;
      }
    } catch (e) {
      print('Error fetching batch prices: $e');
    }
    return {};
  }
}

// Global instance for simple access
final apiService = ApiService();
