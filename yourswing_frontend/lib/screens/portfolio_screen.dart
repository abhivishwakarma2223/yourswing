import 'package:flutter/material.dart';
import 'package:lucide_icons/lucide_icons.dart';
import 'package:google_fonts/google_fonts.dart';
import '../models/portfolio_item.dart';
import '../services/portfolio_service.dart';
import '../services/api_service.dart';
import '../theme/app_theme.dart';
import 'search_screen.dart';

class PortfolioScreen extends StatefulWidget {
  const PortfolioScreen({super.key});

  @override
  State<PortfolioScreen> createState() => _PortfolioScreenState();
}

class _PortfolioScreenState extends State<PortfolioScreen> {
  final PortfolioService _portfolioService = PortfolioService();
  List<PortfolioItem> _holdings = [];
  Map<String, Map<String, double>> _liveData = {};
  bool _isLoading = true;

  @override
  void initState() {
    super.initState();
    _loadPortfolio();
  }

  Future<void> _loadPortfolio() async {
    setState(() => _isLoading = true);
    
    // 1. Load holdings from local storage
    final data = await _portfolioService.getPortfolio();
    _holdings = data;
    
    // 2. Fetch live prices for normalized symbols
    if (_holdings.isNotEmpty) {
      // Ensure we request symbols with .NS suffix for matching
      final symbols = _holdings.map((e) {
        String sym = e.symbol.toUpperCase();
        return sym.contains('.') ? sym : '$sym.NS';
      }).toList();
      
      _liveData = await apiService.fetchLatestPrices(symbols);
    }
    
    setState(() => _isLoading = false);
  }

  void _showAddEditModal({PortfolioItem? item}) {
    final symbolController = TextEditingController(text: item?.symbol ?? '');
    final qtyController = TextEditingController(text: item?.quantity.toString() ?? '');
    final priceController = TextEditingController(text: item?.averagePrice.toString() ?? '');

    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (context) => SingleChildScrollView(
        child: Container(
          padding: EdgeInsets.only(
            bottom: MediaQuery.of(context).viewInsets.bottom + 32,
            left: 24,
            right: 24,
            top: 32,
          ),
          decoration: const BoxDecoration(
            color: Color(0xFF0F172A),
            borderRadius: BorderRadius.vertical(top: Radius.circular(32)),
            border: Border(top: BorderSide(color: Colors.white10)),
          ),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Text(
                    item == null ? 'Add New Stock' : 'Edit Holding',
                    style: GoogleFonts.outfit(
                      color: Colors.white,
                      fontSize: 24,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                  IconButton(
                    onPressed: () => Navigator.pop(context),
                    icon: const Icon(LucideIcons.x, color: Colors.white24),
                  ),
                ],
              ),
              const SizedBox(height: 32),
              _buildTextField(symbolController, 'STOCK SYMBOL', 'e.g. RELIANCE'),
              const SizedBox(height: 20),
              _buildTextField(qtyController, 'QUANTITY', 'e.g. 10', isNumeric: true),
              const SizedBox(height: 20),
              _buildTextField(priceController, 'AVG. BUY PRICE', '₹', isNumeric: true),
              const SizedBox(height: 40),
              SizedBox(
                width: double.infinity,
                height: 56,
                child: ElevatedButton(
                  style: ElevatedButton.styleFrom(
                    backgroundColor: AppTheme.primaryLight,
                    elevation: 0,
                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
                  ),
                  onPressed: () async {
                    if (symbolController.text.isEmpty || qtyController.text.isEmpty || priceController.text.isEmpty) return;
                    
                    String symbol = symbolController.text.trim().toUpperCase();
                    if (!symbol.contains('.')) symbol = '$symbol.NS';

                    final newItem = PortfolioItem(
                      symbol: symbol,
                      name: symbol,
                      quantity: double.tryParse(qtyController.text) ?? 0,
                      averagePrice: double.tryParse(priceController.text) ?? 0,
                    );
                    
                    await _portfolioService.saveStock(newItem);
                    _loadPortfolio();
                    Navigator.pop(context);
                  },
                  child: Text(
                    item == null ? 'SAVE TO PORTFOLIO' : 'UPDATE HOLDING',
                    style: GoogleFonts.outfit(
                      color: Colors.black,
                      fontWeight: FontWeight.w800,
                      fontSize: 15,
                      letterSpacing: 1.2,
                    ),
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildTextField(TextEditingController controller, String label, String hint, {bool isNumeric = false}) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(label, style: GoogleFonts.outfit(color: Colors.white.withOpacity(0.4), fontSize: 11, fontWeight: FontWeight.bold, letterSpacing: 1)),
        const SizedBox(height: 10),
        TextField(
          controller: controller,
          keyboardType: isNumeric ? TextInputType.number : TextInputType.text,
          style: GoogleFonts.outfit(color: Colors.white, fontSize: 16),
          decoration: InputDecoration(
            hintText: hint,
            hintStyle: TextStyle(color: Colors.white.withOpacity(0.1)),
            filled: true,
            fillColor: Colors.white.withOpacity(0.02),
            contentPadding: const EdgeInsets.symmetric(horizontal: 20, vertical: 18),
            border: OutlineInputBorder(
              borderRadius: BorderRadius.circular(16), 
              borderSide: BorderSide(color: Colors.white.withOpacity(0.05)),
            ),
            enabledBorder: OutlineInputBorder(
              borderRadius: BorderRadius.circular(16), 
              borderSide: BorderSide(color: Colors.white.withOpacity(0.05)),
            ),
            focusedBorder: OutlineInputBorder(
              borderRadius: BorderRadius.circular(16), 
              borderSide: const BorderSide(color: AppTheme.primaryLight, width: 1),
            ),
          ),
        ),
      ],
    );
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: const BoxDecoration(
        gradient: LinearGradient(
          colors: [AppTheme.background, AppTheme.backgroundDarker],
          begin: Alignment.topCenter,
          end: Alignment.bottomCenter,
        ),
      ),
      child: Scaffold(
        backgroundColor: Colors.transparent,
        appBar: AppBar(
          backgroundColor: Colors.transparent,
          elevation: 0,
          title: Text(
            'Add & Manage Stocks',
            style: GoogleFonts.outfit(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 24),
          ),
          actions: [
            IconButton(
              icon: const Icon(LucideIcons.refreshCw, color: Colors.white54, size: 20),
              onPressed: _loadPortfolio,
            ),
            const SizedBox(width: 12),
          ],
        ),
        body: _isLoading
            ? const Center(child: CircularProgressIndicator(color: AppTheme.primaryLight))
            : _holdings.isEmpty
                ? _buildEmptyState()
                : ListView.builder(
                    padding: const EdgeInsets.all(24),
                    itemCount: _holdings.length,
                    itemBuilder: (context, index) => _buildHoldingTile(_holdings[index]),
                  ),
        floatingActionButton: FloatingActionButton(
          backgroundColor: AppTheme.primaryLight,
          onPressed: () => _showAddEditModal(),
          child: const Icon(LucideIcons.plus, color: Colors.black),
        ),
      ),
    );
  }

  Widget _buildHoldingTile(PortfolioItem item) {
    // Normalize symbol for lookups
    String lookupSymbol = item.symbol.toUpperCase();
    if (!lookupSymbol.contains('.')) lookupSymbol = '$lookupSymbol.NS';
    
    final stockData = _liveData[lookupSymbol];
    double currentPrice = item.averagePrice;
    double dailyChangePrice = 0.0;
    double dailyChangePercent = 0.0;
    
    bool hasLivePrice = stockData != null && (stockData['price'] ?? 0) > 0;
    if (hasLivePrice) {
      currentPrice = stockData['price']!;
      dailyChangePrice = stockData['change'] ?? 0.0;
      dailyChangePercent = stockData['changePercent'] ?? 0.0;
    }
    
    double totalPnl = (currentPrice - item.averagePrice) * item.quantity;
    double totalPnlPercent = item.averagePrice > 0 
        ? ((currentPrice - item.averagePrice) / item.averagePrice) * 100 
        : 0.0;
        
    bool isProfit = totalPnl >= 0;
    bool isDailyUp = dailyChangePrice >= 0;

    return Container(
      margin: const EdgeInsets.only(bottom: 16),
      padding: const EdgeInsets.all(18),
      decoration: BoxDecoration(
        color: const Color(0xFF111827),
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: Colors.white.withOpacity(0.05)),
      ),
      child: Column(
        children: [
          Row(
            children: [
              Container(
                width: 44,
                height: 44,
                decoration: BoxDecoration(
                  color: AppTheme.primaryLight.withOpacity(0.1),
                  borderRadius: BorderRadius.circular(12),
                ),
                child: const Icon(LucideIcons.barChart2, color: AppTheme.primaryLight, size: 20),
              ),
              const SizedBox(width: 14),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      item.symbol, 
                      style: GoogleFonts.outfit(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 17),
                    ),
                    Text(
                      '${item.quantity.toInt()} @ ₹${item.averagePrice}', 
                      style: GoogleFonts.outfit(color: Colors.white38, fontSize: 12),
                    ),
                  ],
                ),
              ),
              Column(
                crossAxisAlignment: CrossAxisAlignment.end,
                children: [
                  Text(
                    '₹${currentPrice.toStringAsFixed(2)}',
                    style: GoogleFonts.outfit(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 16),
                  ),
                  Text(
                    'Live Price',
                    style: GoogleFonts.outfit(color: Colors.white24, fontSize: 10),
                  ),
                ],
              ),
              const SizedBox(width: 4),
              PopupMenuButton<String>(
                icon: const Icon(LucideIcons.moreVertical, color: Colors.white24, size: 18),
                padding: EdgeInsets.zero,
                constraints: const BoxConstraints(),
                onSelected: (value) async {
                  if (value == 'edit') {
                    _showAddEditModal(item: item);
                  } else if (value == 'delete') {
                    await _portfolioService.deleteStock(item.symbol);
                    _loadPortfolio();
                  }
                },
                itemBuilder: (context) => [
                  const PopupMenuItem(value: 'edit', child: Text('Edit')),
                  const PopupMenuItem(value: 'delete', child: Text('Delete')),
                ],
              ),
            ],
          ),
          const SizedBox(height: 16),
          Container(height: 1, color: Colors.white.withOpacity(0.03)),
          const SizedBox(height: 16),
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              // Total P&L
              Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text('TOTAL P&L', style: GoogleFonts.outfit(color: Colors.white24, fontSize: 10, fontWeight: FontWeight.bold, letterSpacing: 0.5)),
                  const SizedBox(height: 4),
                  Text(
                    '${isProfit ? '+' : ''}₹${totalPnl.abs().toStringAsFixed(2)} (${totalPnlPercent.abs().toStringAsFixed(1)}%)',
                    style: GoogleFonts.outfit(
                      color: isProfit ? AppTheme.signalBuy : AppTheme.signalAvoid,
                      fontSize: 14,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                ],
              ),
              // Today's Change
              Column(
                crossAxisAlignment: CrossAxisAlignment.end,
                children: [
                  Text('TODAY', style: GoogleFonts.outfit(color: Colors.white24, fontSize: 10, fontWeight: FontWeight.bold, letterSpacing: 0.5)),
                  const SizedBox(height: 4),
                  Text(
                    '${isDailyUp ? '+' : ''}₹${dailyChangePrice.abs().toStringAsFixed(2)} (${dailyChangePercent.abs().toStringAsFixed(1)}%)',
                    style: TextStyle(
                      color: isDailyUp ? AppTheme.signalBuy : AppTheme.signalAvoid,
                      fontSize: 14,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                ],
              ),
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildEmptyState() {
    return Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Icon(LucideIcons.package, size: 80, color: Colors.white.withOpacity(0.05)),
          const SizedBox(height: 24),
          Text(
            'Your portfolio is empty', 
            style: GoogleFonts.outfit(color: Colors.white.withOpacity(0.3), fontSize: 18, fontWeight: FontWeight.w500),
          ),
          const SizedBox(height: 8),
          Text(
            'Tap + to add your first stock', 
            style: GoogleFonts.outfit(color: Colors.white.withOpacity(0.15), fontSize: 14),
          ),
        ],
      ),
    );
  }
}
