import 'package:flutter/material.dart';
import 'package:flutter_animate/flutter_animate.dart';
import 'package:lucide_icons/lucide_icons.dart';
import '../theme/app_theme.dart';
import '../widgets/premium_card.dart';
import '../widgets/indicator_card.dart';
import '../services/api_service.dart';

class ResultScreen extends StatefulWidget {
  final String symbol;

  const ResultScreen({super.key, required this.symbol});

  @override
  State<ResultScreen> createState() => _ResultScreenState();
}

class _ResultScreenState extends State<ResultScreen> {
  Map<String, dynamic>? data;
  bool isLoading = true;

  @override
  void initState() {
    super.initState();
    _fetchData();
  }

  Future<void> _fetchData() async {
    final result = await apiService.fetchStockAnalysis(widget.symbol);
    setState(() {
      data = result;
      isLoading = false;
    });
  }

  @override
  Widget build(BuildContext context) {
    if (isLoading) {
      return const Scaffold(
        body: Center(child: CircularProgressIndicator(color: AppTheme.primaryLight)),
      );
    }

    if (data == null) {
      return const Scaffold(
        body: Center(child: Text('Failed to load data')),
      );
    }

    final isPositive = data!['change'] > 0;
    final signalStr = data!['signal']?.toString().toLowerCase() ?? 'watch';
    
    Color signalColor;
    IconData signalIcon;
    
    if (signalStr == 'buy') {
      signalColor = AppTheme.signalBuy;
      signalIcon = LucideIcons.trendingUp;
    } else if (signalStr == 'avoid') {
      signalColor = AppTheme.signalAvoid;
      signalIcon = LucideIcons.trendingDown;
    } else {
      signalColor = AppTheme.signalNeutral;
      signalIcon = LucideIcons.eye;
    }

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
        leading: IconButton(
          icon: const Icon(LucideIcons.arrowLeft, color: AppTheme.textDark),
          onPressed: () => Navigator.pop(context),
        ),
        actions: [
          IconButton(
            icon: const Icon(LucideIcons.star, color: AppTheme.textMuted),
            onPressed: () {},
          ),
        ],
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(24.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Header: Symbol & Price
            Text(
              data!['symbol'],
              style: Theme.of(context).textTheme.displayLarge,
            ).animate().fade().slideY(begin: -0.2),
            
            const SizedBox(height: 8),
            
            Row(
              crossAxisAlignment: CrossAxisAlignment.end,
              children: [
                Text(
                  '₹${data!['price']}',
                  style: const TextStyle(
                    fontSize: 48,
                    fontWeight: FontWeight.bold,
                    color: AppTheme.textDark,
                    letterSpacing: -1.5,
                  ),
                ),
                const SizedBox(width: 12),
                Padding(
                  padding: const EdgeInsets.only(bottom: 8.0),
                  child: Text(
                    '${isPositive ? '+' : ''}${data!['change']} (${data!['changePercent']}%)',
                    style: TextStyle(
                      fontSize: 18,
                      fontWeight: FontWeight.w600,
                      color: isPositive ? AppTheme.signalBuy : AppTheme.signalAvoid,
                    ),
                  ),
                ),
              ],
            ).animate().fade(delay: 100.ms).slideY(begin: 0.2),

            const SizedBox(height: 32),

            // Signal Card
            PremiumCard(
              color: signalColor.withOpacity(0.1),
              child: Row(
                children: [
                  Container(
                    padding: const EdgeInsets.all(12),
                    decoration: BoxDecoration(
                      color: signalColor,
                      shape: BoxShape.circle,
                    ),
                    child: Icon(
                      signalIcon,
                      color: Colors.white,
                    ),
                  ),
                  const SizedBox(width: 16),
                  Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        'Overall Signal',
                        style: TextStyle(
                          color: Colors.white.withOpacity(0.7),
                          fontWeight: FontWeight.w500,
                        ),
                      ),
                      Text(
                        data!['signal'],
                        style: TextStyle(
                          color: signalColor,
                          fontSize: 24,
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                    ],
                  ),
                ],
              ),
            ).animate().fade(delay: 200.ms).scale(),

            const SizedBox(height: 32),

            // Indicators Grid
            Text(
              'Technical Indicators',
              style: Theme.of(context).textTheme.titleLarge,
            ).animate().fade(delay: 300.ms),
            
            const SizedBox(height: 16),

            GridView.count(
              crossAxisCount: 2,
              crossAxisSpacing: 16,
              mainAxisSpacing: 16,
              shrinkWrap: true,
              physics: const NeverScrollableScrollPhysics(),
              childAspectRatio: 1.8,
              children: [
                IndicatorCard(
                  title: 'RSI (14)',
                  value: '${data!['indicators']['RSI']['value']}',
                ),
                IndicatorCard(
                  title: 'EMA (20)',
                  value: '₹${data!['indicators']['EMA20']['value']}',
                ),
                IndicatorCard(
                  title: 'EMA (50)',
                  value: '₹${data!['indicators']['EMA50']['value']}',
                ),
                IndicatorCard(
                  title: 'MACD',
                  value: '${data!['macd']}',
                ),
                IndicatorCard(
                  title: 'ATR',
                  value: '₹${data!['atr']}',
                ),
                IndicatorCard(
                  title: 'Volume Ratio',
                  value: '${data!['volume_ratio']}x',
                ),
                IndicatorCard(
                  title: 'Rel. Strength',
                  value: '${data!['relative_strength']}',
                ),
                IndicatorCard(
                  title: 'Breakout',
                  value: data!['breakout'] == true ? 'YES' : 'NO',
                ),
              ],
            ).animate().fade(delay: 400.ms).slideY(begin: 0.1),
          ],
        ),
      ),
      ),
    );
  }
}
