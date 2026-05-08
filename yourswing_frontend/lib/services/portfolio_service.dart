import 'dart:convert';
import 'package:shared_preferences/shared_preferences.dart';
import '../models/portfolio_item.dart';

class PortfolioService {
  static const String _key = 'user_portfolio';

  Future<void> saveStock(PortfolioItem item) async {
    final prefs = await SharedPreferences.getInstance();
    final List<PortfolioItem> currentList = await getPortfolio();
    
    // Check if already exists to avoid duplicates
    final index = currentList.indexWhere((e) => e.symbol == item.symbol);
    if (index != -1) {
      currentList[index] = item;
    } else {
      currentList.add(item);
    }
    
    await _saveList(prefs, currentList);
  }

  Future<void> deleteStock(String symbol) async {
    final prefs = await SharedPreferences.getInstance();
    final List<PortfolioItem> currentList = await getPortfolio();
    currentList.removeWhere((item) => item.symbol == symbol);
    await _saveList(prefs, currentList);
  }

  Future<List<PortfolioItem>> getPortfolio() async {
    final prefs = await SharedPreferences.getInstance();
    final String? data = prefs.getString(_key);
    if (data == null) return [];
    
    final List decodedData = jsonDecode(data);
    return decodedData.map((e) => PortfolioItem.fromMap(e)).toList();
  }

  Future<void> _saveList(SharedPreferences prefs, List<PortfolioItem> list) async {
    final String encodedData = jsonEncode(list.map((e) => e.toMap()).toList());
    await prefs.setString(_key, encodedData);
  }
}
