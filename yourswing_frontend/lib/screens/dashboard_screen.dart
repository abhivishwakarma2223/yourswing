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
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              'Welcome back,',
                              style: GoogleFonts.outfit(
                                color: Colors.white.withOpacity(0.5),
                                fontSize: 14,
                                fontWeight: FontWeight.w500,
                              ),
                            ),
                            Text(
                              'Abhivishwakarma',
                              style: GoogleFonts.outfit(
                                color: Colors.white,
                                fontSize: 26,
                                fontWeight: FontWeight.bold,
                                letterSpacing: -0.5,
                              ),
                            ),
                          ],
                        ),
                      ),
                      Stack(
                        children: [
                          Container(
                            width: 52,
                            height: 52,
                            decoration: BoxDecoration(
                              gradient: LinearGradient(
                                colors: [
                                  AppTheme.primaryLight.withOpacity(0.2),
                                  AppTheme.primaryLight.withOpacity(0.05),
                                ],
                                begin: Alignment.topLeft,
                                end: Alignment.bottomRight,
                              ),
                              shape: BoxShape.circle,
                              border: Border.all(
                                color: AppTheme.primaryLight.withOpacity(0.2),
                                width: 1.5,
                              ),
                            ),
                            child: const Icon(
                              LucideIcons.user,
                              color: AppTheme.primaryLight,
                              size: 24,
                            ),
                          ),
                          Positioned(
                            right: 2,
                            top: 2,
                            child: Container(
                              width: 12,
                              height: 12,
                              decoration: BoxDecoration(
                                color: AppTheme.primaryLight,
                                shape: BoxShape.circle,
                                border: Border.all(color: AppTheme.background, width: 2),
                              ),
                            ),
                          ),
                        ],
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
        borderRadius: BorderRadius.circular(28),
        gradient: LinearGradient(
          colors: [
            const Color(0xFF1E293B),
            const Color(0xFF0F172A).withOpacity(0.8),
          ],
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
        ),
        border: Border.all(
          color: Colors.white.withOpacity(0.08),
          width: 1.5,
        ),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withOpacity(0.4),
            blurRadius: 24,
            offset: const Offset(0, 12),
          ),
          BoxShadow(
            color: AppTheme.primaryLight.withOpacity(0.05),
            blurRadius: 40,
            spreadRadius: -10,
          )
        ],
      ),
      clipBehavior: Clip.antiAlias,
      child: Stack(
        children: [
          // Background Decorative Circle
          Positioned(
            right: -50,
            top: -50,
            child: Container(
              width: 150,
              height: 150,
              decoration: BoxDecoration(
                color: AppTheme.primaryLight.withOpacity(0.03),
                shape: BoxShape.circle,
              ),
            ),
          ),
          Padding(
            padding: const EdgeInsets.all(28),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Expanded(
                      child: Text(
                        'Total Portfolio Value',
                        style: GoogleFonts.outfit(
                          color: Colors.white.withOpacity(0.5),
                          fontSize: 15,
                          fontWeight: FontWeight.w500,
                          letterSpacing: 0.2,
                        ),
                      ),
                    ),
                    Container(
                      decoration: BoxDecoration(
                        color: Colors.white.withOpacity(0.05),
                        borderRadius: BorderRadius.circular(10),
                      ),
                      child: IconButton(
                        visualDensity: VisualDensity.compact,
                        padding: const EdgeInsets.all(4),
                        constraints: const BoxConstraints(),
                        icon: Icon(LucideIcons.refreshCw, color: Colors.white.withOpacity(0.4), size: 16),
                        onPressed: _loadData,
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 12),
                FittedBox(
                  fit: BoxFit.scaleDown,
                  alignment: Alignment.centerLeft,
                  child: Text(
                    '₹${stats['total']!.toStringAsFixed(2)}',
                    style: GoogleFonts.outfit(
                      color: Colors.white,
                      fontSize: 42,
                      fontWeight: FontWeight.bold,
                      letterSpacing: -1.5,
                    ),
                  ),
                ),
                const SizedBox(height: 20),
                FittedBox(
                  fit: BoxFit.scaleDown,
                  alignment: Alignment.centerLeft,
                  child: Row(
                    children: [
                      Container(
                        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                        decoration: BoxDecoration(
                          color: (isProfit ? AppTheme.signalBuy : AppTheme.signalAvoid).withOpacity(0.12),
                          borderRadius: BorderRadius.circular(14),
                          border: Border.all(
                            color: (isProfit ? AppTheme.signalBuy : AppTheme.signalAvoid).withOpacity(0.2),
                          ),
                        ),
                        child: Row(
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            Icon(
                              isProfit ? LucideIcons.trendingUp : LucideIcons.trendingDown,
                              color: isProfit ? AppTheme.signalBuy : AppTheme.signalAvoid,
                              size: 16,
                            ),
                            const SizedBox(width: 8),
                            Text(
                              '${isProfit ? '+' : ''}₹${stats['pnl']!.toStringAsFixed(2)} (${stats['percent']!.toStringAsFixed(1)}%)',
                              style: GoogleFonts.outfit(
                                color: isProfit ? AppTheme.signalBuy : AppTheme.signalAvoid,
                                fontWeight: FontWeight.bold,
                                fontSize: 14,
                              ),
                            ),
                          ],
                        ),
                      ),
                      const SizedBox(width: 14),
                      Text(
                        'Live Performance',
                        style: GoogleFonts.outfit(
                          color: Colors.white.withOpacity(0.3),
                          fontSize: 13,
                          fontWeight: FontWeight.w400,
                        ),
                      )
                    ],
                  ),
                )
              ],
            ),
          ),
        ],
      ),
    ).animate().fade(delay: 100.ms).slideY(begin: 0.2, curve: Curves.easeOutQuad);
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
      padding: const EdgeInsets.only(bottom: 16),
      child: PremiumCard(
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 16),
        child: Row(
          children: [
            // Score indicator
            Stack(
              alignment: Alignment.center,
              children: [
                SizedBox(
                  width: 48,
                  height: 48,
                  child: CircularProgressIndicator(
                    value: score / 100.0,
                    backgroundColor: Colors.white.withOpacity(0.03),
                    color: badgeColor.withOpacity(0.8),
                    strokeWidth: 4,
                    strokeCap: StrokeCap.round,
                  ),
                ),
                Text(
                  score.toStringAsFixed(1),
                  style: GoogleFonts.outfit(
                    color: badgeColor,
                    fontWeight: FontWeight.bold,
                    fontSize: 14, // Slightly smaller to fit decimals
                  ),
                ),
              ],
            ),
            const SizedBox(width: 16),
            
            // Symbol and Signal
            Expanded(
              flex: 3,
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    stock['symbol'],
                    style: GoogleFonts.outfit(
                      fontWeight: FontWeight.bold,
                      fontSize: 17,
                      color: Colors.white,
                    ),
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                  ),
                  const SizedBox(height: 4),
                  if (signal != null)
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                      decoration: BoxDecoration(
                        color: badgeColor.withOpacity(0.12),
                        borderRadius: BorderRadius.circular(6),
                        border: Border.all(color: badgeColor.withOpacity(0.3), width: 1),
                      ),
                      child: Text(
                        signal.toUpperCase(),
                        style: GoogleFonts.outfit(
                          color: badgeColor,
                          fontSize: 10,
                          fontWeight: FontWeight.w800,
                          letterSpacing: 0.5,
                        ),
                      ),
                    ),
                ],
              ),
            ),
            
            // Price and Change
            Expanded(
              flex: 2,
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.end,
                children: [
                  FittedBox(
                    fit: BoxFit.scaleDown,
                    child: Text(
                      '₹${price.toStringAsFixed(2)}',
                      style: GoogleFonts.outfit(
                        fontWeight: FontWeight.bold,
                        fontSize: 18,
                        color: Colors.white,
                        letterSpacing: -0.5,
                      ),
                    ),
                  ),
                  const SizedBox(height: 2),
                  FittedBox(
                    fit: BoxFit.scaleDown,
                    child: Text(
                      '${changePercent > 0 ? '+' : ''}${changePercent.toStringAsFixed(2)}%',
                      style: GoogleFonts.outfit(
                        color: changePercent > 0 ? AppTheme.signalBuy : AppTheme.signalAvoid,
                        fontSize: 13,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    ).animate().fade(delay: 400.ms).slideX(begin: 0.1, curve: Curves.easeOutQuad);
  }
}
