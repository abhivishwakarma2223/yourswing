import 'package:flutter/material.dart';
import 'package:flutter_animate/flutter_animate.dart';
import 'package:lucide_icons/lucide_icons.dart';
import 'package:google_fonts/google_fonts.dart';
import '../theme/app_theme.dart';
import '../widgets/premium_card.dart';
import '../widgets/custom_button.dart';
import '../services/api_service.dart';
import '../services/portfolio_service.dart';
import '../models/portfolio_item.dart';
import 'search_screen.dart';

class DashboardScreen extends StatefulWidget {
  const DashboardScreen({super.key});

  @override
  State<DashboardScreen> createState() => _DashboardScreenState();
}

class _DashboardScreenState extends State<DashboardScreen> {
  final PortfolioService _portfolioService = PortfolioService();
  List<Map<String, dynamic>> trending = [];
  List<PortfolioItem> _holdings = [];
  Map<String, Map<String, double>> _livePrices = {};
  bool _isLoading = true;

  @override
  void initState() {
    super.initState();
    _loadData();
  }

  Future<void> _loadData() async {
    setState(() => _isLoading = true);
    
    // 1. Load Trending Stocks
    final trendingData = await apiService.getTrendingStocks();
    
    // 2. Load Portfolio Holdings
    final holdingsData = await _portfolioService.getPortfolio();
    
    // 3. Fetch Live Prices for Holdings (Normalized)
    Map<String, Map<String, double>> prices = {};
    if (holdingsData.isNotEmpty) {
      final symbols = holdingsData.map((e) {
        String sym = e.symbol.toUpperCase();
        return sym.contains('.') ? sym : '$sym.NS';
      }).toList();
      prices = await apiService.fetchLatestPrices(symbols);
    }

    setState(() {
      trending = trendingData;
      _holdings = holdingsData;
      _livePrices = prices;
      _isLoading = false;
    });
  }

  Map<String, double> _calculateStats() {
    double totalValue = 0;
    double totalInvestment = 0;
    for (var item in _holdings) {
      String symbol = item.symbol.toUpperCase();
      if (!symbol.contains('.')) symbol = '$symbol.NS';
      
      final stockData = _livePrices[symbol];
      double currentPrice = item.averagePrice;
      
      if (stockData != null && (stockData['price'] ?? 0) > 0) {
        currentPrice = stockData['price']!;
      }
      
      totalValue += currentPrice * item.quantity;
      totalInvestment += item.averagePrice * item.quantity;
    }
    double pnl = totalValue - totalInvestment;
    double pnlPercent = totalInvestment > 0 ? (pnl / totalInvestment) * 100 : 0;
    return {'total': totalValue, 'pnl': pnl, 'percent': pnlPercent};
  }

  @override
  Widget build(BuildContext context) {
    final stats = _calculateStats();

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
        body: SafeArea(
          child: RefreshIndicator(
            onRefresh: _loadData,
            color: AppTheme.primaryLight,
            backgroundColor: const Color(0xFF111827),
            child: SingleChildScrollView(
              padding: const EdgeInsets.all(24),
              physics: const AlwaysScrollableScrollPhysics(),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  // Header
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            'Welcome back,',
                            style: GoogleFonts.outfit(color: Colors.white60, fontSize: 14),
                          ),
                          Text(
                            'Abhivishwakarma',
                            style: GoogleFonts.outfit(color: Colors.white, fontSize: 24, fontWeight: FontWeight.bold),
                          ),
                        ],
                      ),
                      Container(
                        width: 48,
                        height: 48,
                        decoration: BoxDecoration(
                          color: AppTheme.primaryLight.withOpacity(0.1),
                          shape: BoxShape.circle,
                        ),
                        child: const Icon(
                          LucideIcons.user,
                          color: AppTheme.primaryDark,
                        ),
                      )
                    ],
                  ).animate().fade().slideY(begin: -0.2),

                  const SizedBox(height: 32),

                  // Portfolio Summary Card (Now Dynamic)
                  _buildDynamicSummaryCard(stats),

                  const SizedBox(height: 32),

                  // CTA
                  CustomButton(
                    text: 'Search ',
                    icon: LucideIcons.search,
                    onPressed: () async {
                      await Navigator.push(
                        context,
                        MaterialPageRoute(builder: (_) => const SearchScreen()),
                      );
                      _loadData(); // Refresh data after returning
                    },
                  ).animate().fade(delay: 200.ms).scale(),

                  const SizedBox(height: 32),

                  // Trending Section
                  Text(
                    'Trending Now',
                    style: GoogleFonts.outfit(color: Colors.white, fontSize: 20, fontWeight: FontWeight.bold),
                  ).animate().fade(delay: 300.ms),
                  const SizedBox(height: 16),

                  if (_isLoading)
                    const Center(child: CircularProgressIndicator(color: AppTheme.primaryLight))
                  else
                    ...trending.map((stock) => _buildTrendingTile(stock)),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildDynamicSummaryCard(Map<String, double> stats) {
    bool isProfit = stats['pnl']! >= 0;
    return Container(
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(24),
        gradient: const LinearGradient(
          colors: [Color(0xFF1E293B), Color(0xFF0F172A)],
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
        ),
        border: Border.all(
          color: AppTheme.primaryLight.withOpacity(0.4),
          width: 1.0,
        ),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withOpacity(0.2),
            blurRadius: 20,
            offset: const Offset(0, 10),
          )
        ],
      ),
      padding: const EdgeInsets.all(24),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text(
                'Total Portfolio',
                style: GoogleFonts.outfit(color: Colors.white60, fontSize: 16),
              ),
              IconButton(
                visualDensity: VisualDensity.compact,
                padding: EdgeInsets.zero,
                constraints: const BoxConstraints(),
                icon: const Icon(LucideIcons.refreshCw, color: Colors.white24, size: 18),
                onPressed: _loadData,
              ),
            ],
          ),
          const SizedBox(height: 8),
          Text(
            '₹${stats['total']!.toStringAsFixed(2)}',
            style: GoogleFonts.outfit(
              color: Colors.white,
              fontSize: 36,
              fontWeight: FontWeight.bold,
              letterSpacing: -1,
            ),
          ),
          const SizedBox(height: 16),
          Row(
            children: [
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                decoration: BoxDecoration(
                  color: (isProfit ? AppTheme.signalBuy : AppTheme.signalAvoid).withOpacity(0.15),
                  borderRadius: BorderRadius.circular(10),
                  border: Border.all(color: (isProfit ? AppTheme.signalBuy : AppTheme.signalAvoid).withOpacity(0.3)),
                ),
                child: Row(
                  children: [
                    Icon(
                      isProfit ? LucideIcons.trendingUp : LucideIcons.trendingDown,
                      color: isProfit ? AppTheme.signalBuy : AppTheme.signalAvoid,
                      size: 16,
                    ),
                    const SizedBox(width: 6),
                    Text(
                      '${isProfit ? '+' : ''}₹${stats['pnl']!.toStringAsFixed(2)} (${stats['percent']!.toStringAsFixed(1)}%)',
                      style: TextStyle(
                        color: isProfit ? AppTheme.signalBuy : AppTheme.signalAvoid,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(width: 12),
              Text(
                'Live Gain',
                style: GoogleFonts.outfit(color: Colors.white38, fontSize: 13),
              )
            ],
          )
        ],
      ),
    ).animate().fade(delay: 100.ms).slideY(begin: 0.2);
  }

  Widget _buildTrendingTile(Map<String, dynamic> stock) {
    final double price = (stock['price'] ?? 0.0).toDouble();
    final double changePercent = (stock['changePercent'] ?? stock['change'] ?? 0.0).toDouble();
    final String? signal = stock['signal']?.toString();
    final String signalType = (signal ?? 'watch').toLowerCase();
    final double score = (stock['score'] ?? 0.0).toDouble();
    
    Color badgeColor;
    if (signalType.contains('buy')) badgeColor = AppTheme.signalBuy;
    else if (signalType == 'avoid') badgeColor = AppTheme.signalAvoid;
    else badgeColor = AppTheme.signalNeutral;
    
    return Padding(
      padding: const EdgeInsets.only(bottom: 12),
      child: PremiumCard(
        padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 16),
        child: Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Row(
              children: [
                Stack(
                  alignment: Alignment.center,
                  children: [
                    SizedBox(
                      width: 44,
                      height: 44,
                      child: CircularProgressIndicator(
                        value: score / 100.0,
                        backgroundColor: Colors.white.withOpacity(0.05),
                        color: badgeColor,
                        strokeWidth: 3.5,
                        strokeCap: StrokeCap.round,
                      ),
                    ),
                    Text(
                      score.toInt().toString(),
                      style: GoogleFonts.outfit(
                        color: badgeColor,
                        fontWeight: FontWeight.bold,
                        fontSize: 16,
                      ),
                    ),
                  ],
                ),
                const SizedBox(width: 16),
                Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        Text(
                          stock['symbol'],
                          style: GoogleFonts.outfit(fontWeight: FontWeight.w600, fontSize: 16, color: Colors.white),
                        ),
                        const SizedBox(width: 8),
                        if (signal != null)
                          Container(
                            padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                            decoration: BoxDecoration(
                              color: badgeColor.withOpacity(0.1),
                              border: Border.all(color: badgeColor, width: 1),
                              borderRadius: BorderRadius.circular(6),
                            ),
                            child: Text(
                              signal.toUpperCase(),
                              style: TextStyle(color: badgeColor, fontSize: 10, fontWeight: FontWeight.bold),
                            ),
                          ),
                      ],
                    ),
                  ],
                ),
              ],
            ),
            Column(
              crossAxisAlignment: CrossAxisAlignment.end,
              children: [
                Text(
                  '₹$price',
                  style: GoogleFonts.outfit(fontWeight: FontWeight.w600, fontSize: 16, color: Colors.white),
                ),
                Text(
                  '${changePercent > 0 ? '+' : ''}₹${(stock['change'] ?? 0.0).toStringAsFixed(2)} (${changePercent.toStringAsFixed(1)}%)',
                  style: TextStyle(
                    color: changePercent > 0 ? AppTheme.signalBuy : AppTheme.signalAvoid,
                    fontSize: 12,
                    fontWeight: FontWeight.w500,
                  ),
                ),
              ],
            ),
          ],
        ),
      ),
    ).animate().fade(delay: 400.ms).slideX(begin: 0.1);
  }
}
