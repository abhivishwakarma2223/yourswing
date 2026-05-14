import 'package:flutter/material.dart';
import 'package:flutter_animate/flutter_animate.dart';
import 'package:lucide_icons/lucide_icons.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:provider/provider.dart';
import '../theme/app_theme.dart';
import '../widgets/premium_card.dart';
import '../widgets/custom_button.dart';
import '../services/api_service.dart';
import '../models/portfolio_item.dart';
import '../providers/portfolio_provider.dart';
import 'search_screen.dart';

class DashboardScreen extends StatefulWidget {
  const DashboardScreen({super.key});

  @override
  State<DashboardScreen> createState() => _DashboardScreenState();
}

class _DashboardScreenState extends State<DashboardScreen> {
  List<Map<String, dynamic>> trending = [];
  bool _isTrendingLoading = true;

  @override
  void initState() {
    super.initState();
    _loadTrending();
    // Initial portfolio load is handled by Provider constructor
  }

  Future<void> _loadTrending() async {
    setState(() => _isTrendingLoading = true);
    final data = await apiService.getTrendingStocks();
    setState(() {
      trending = data;
      _isTrendingLoading = false;
    });
  }

  Future<void> _refreshAll() async {
    await Future.wait([
      _loadTrending(),
      context.read<PortfolioProvider>().loadPortfolio(),
    ]);
  }

  @override
  Widget build(BuildContext context) {
    return Consumer<PortfolioProvider>(
      builder: (context, portfolio, child) {
        final stats = portfolio.getSummary();

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
                onRefresh: _refreshAll,
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
                      _buildDynamicSummaryCard(stats, portfolio.isLoading),

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
                          // No need to manually refresh, Provider will be updated if search screen modifies portfolio
                        },
                      ).animate().fade(delay: 200.ms).scale(),

                      const SizedBox(height: 32),

                      // Trending Section
                      Text(
                        'Trending Now',
                        style: GoogleFonts.outfit(color: Colors.white, fontSize: 20, fontWeight: FontWeight.bold),
                      ).animate().fade(delay: 300.ms),
                      const SizedBox(height: 16),

                      if (_isTrendingLoading)
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
      },
    );
  }

  Widget _buildDynamicSummaryCard(Map<String, double> stats, bool isPortfolioLoading) {
    bool isProfit = (stats['pnl'] ?? 0) >= 0;
    final double dailyChange = stats['dailyChange'] ?? 0;
    final bool isDailyUp = dailyChange >= 0;
    final double invested = stats['invested'] ?? 0;
    final double current = stats['current'] ?? 0;

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
                // Header row
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
                        icon: isPortfolioLoading
                            ? const SizedBox(width: 14, height: 14, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white))
                            : Icon(LucideIcons.refreshCw, color: Colors.white.withOpacity(0.4), size: 16),
                        onPressed: _refreshAll,
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 12),

                // Big current value number
                FittedBox(
                  fit: BoxFit.scaleDown,
                  alignment: Alignment.centerLeft,
                  child: Text(
                    '₹${current.toStringAsFixed(2)}',
                    style: GoogleFonts.outfit(
                      color: Colors.white,
                      fontSize: 42,
                      fontWeight: FontWeight.bold,
                      letterSpacing: -1.5,
                    ),
                  ),
                ),
                const SizedBox(height: 16),

                // P&L pill + Today's change pill
                Wrap(
                  spacing: 10,
                  runSpacing: 8,
                  children: [
                    // Overall P&L
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
                            size: 15,
                          ),
                          const SizedBox(width: 6),
                          Text(
                            '${isProfit ? '+' : ''}₹${(stats['pnl'] ?? 0).toStringAsFixed(0)}  (${(stats['percent'] ?? 0).toStringAsFixed(1)}%)',
                            style: GoogleFonts.outfit(
                              color: isProfit ? AppTheme.signalBuy : AppTheme.signalAvoid,
                              fontWeight: FontWeight.bold,
                              fontSize: 13,
                            ),
                          ),
                        ],
                      ),
                    ),
                    // Today's change pill
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                      decoration: BoxDecoration(
                        color: (isDailyUp ? AppTheme.signalBuy : AppTheme.signalAvoid).withOpacity(0.08),
                        borderRadius: BorderRadius.circular(14),
                        border: Border.all(
                          color: (isDailyUp ? AppTheme.signalBuy : AppTheme.signalAvoid).withOpacity(0.15),
                        ),
                      ),
                      child: Row(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          Icon(
                            isDailyUp ? LucideIcons.arrowUpRight : LucideIcons.arrowDownRight,
                            color: isDailyUp ? AppTheme.signalBuy : AppTheme.signalAvoid,
                            size: 15,
                          ),
                          const SizedBox(width: 6),
                          Text(
                            'Today  ${isDailyUp ? '+' : '-'}₹${dailyChange.abs().toStringAsFixed(0)}',
                            style: GoogleFonts.outfit(
                              color: isDailyUp ? AppTheme.signalBuy : AppTheme.signalAvoid,
                              fontWeight: FontWeight.bold,
                              fontSize: 13,
                            ),
                          ),
                        ],
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 20),

                // Divider
                Container(height: 1, color: Colors.white.withOpacity(0.06)),
                const SizedBox(height: 16),

                // Invested vs Current 2-col stats
                Row(
                  children: [
                    Expanded(
                      child: _buildDashStat(
                        'Invested',
                        '₹${invested.toStringAsFixed(2)}',
                        LucideIcons.wallet,
                        Colors.white38,
                      ),
                    ),
                    Container(width: 1, height: 36, color: Colors.white.withOpacity(0.07)),
                    Expanded(
                      child: _buildDashStat(
                        'Current',
                        '₹${current.toStringAsFixed(2)}',
                        LucideIcons.barChart2,
                        AppTheme.primaryLight.withOpacity(0.8),
                        align: TextAlign.right,
                      ),
                    ),
                  ],
                ),
              ],
            ),
          ),
        ],
      ),
    ).animate().fade(delay: 100.ms).slideY(begin: 0.2, curve: Curves.easeOutQuad);
  }

  Widget _buildDashStat(String label, String value, IconData icon, Color color, {TextAlign align = TextAlign.left}) {
    final isRight = align == TextAlign.right;
    return Padding(
      padding: EdgeInsets.only(left: isRight ? 16 : 0, right: isRight ? 0 : 16),
      child: Column(
        crossAxisAlignment: isRight ? CrossAxisAlignment.end : CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: isRight ? MainAxisAlignment.end : MainAxisAlignment.start,
            children: [
              if (!isRight) ...[
                Icon(icon, size: 11, color: Colors.white24),
                const SizedBox(width: 4),
              ],
              Text(
                label,
                style: GoogleFonts.outfit(
                  color: Colors.white24,
                  fontSize: 11,
                  letterSpacing: 0.2,
                ),
              ),
              if (isRight) ...[
                const SizedBox(width: 4),
                Icon(icon, size: 11, color: Colors.white24),
              ],
            ],
          ),
          const SizedBox(height: 4),
          FittedBox(
            fit: BoxFit.scaleDown,
            alignment: isRight ? Alignment.centerRight : Alignment.centerLeft,
            child: Text(
              value,
              style: GoogleFonts.outfit(
                color: color,
                fontSize: 14,
                fontWeight: FontWeight.w700,
              ),
            ),
          ),
        ],
      ),
    );
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
