import 'dart:convert';
import 'package:http/http.dart' as http;

class ApiService {
  // Use 10.0.2.2 if testing on an Android Emulator
  // Use 127.0.0.1 or localhost if testing on Windows/Chrome
  final String baseUrl = 'http://127.0.0.1:8001/api';

  Future<Map<String, dynamic>?> fetchStockAnalysis(String symbol) async {
    try {
      final response = await http.get(Uri.parse('$baseUrl/analysis/$symbol'));
      
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

  // Fetch multiple prices in parallel
  Future<Map<String, double>> fetchLatestPrices(List<String> symbols) async {
    Map<String, double> prices = {};
    try {
      // Run all requests at the same time for speed
      final results = await Future.wait(
        symbols.map((s) => fetchStockAnalysis(s))
      );
      
      for (int i = 0; i < symbols.length; i++) {
        if (results[i] != null) {
          prices[symbols[i]] = (results[i]!['price'] ?? 0.0).toDouble();
        }
      }
    } catch (e) {
      print('Error fetching multiple prices: $e');
    }
    return prices;
  }
}

// Global instance for simple access
final apiService = ApiService();
