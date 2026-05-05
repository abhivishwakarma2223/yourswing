import 'package:flutter/material.dart';
import 'package:flutter_animate/flutter_animate.dart';
import 'package:lucide_icons/lucide_icons.dart';
import '../theme/app_theme.dart';
import '../widgets/premium_card.dart';
import '../widgets/custom_button.dart';
import '../services/api_service.dart';
import 'search_screen.dart';

class DashboardScreen extends StatefulWidget {
  const DashboardScreen({super.key});

  @override
  State<DashboardScreen> createState() => _DashboardScreenState();
}

class _DashboardScreenState extends State<DashboardScreen> {
  List<Map<String, dynamic>> trending = [];

  @override
  void initState() {
    super.initState();
    _loadData();
  }

  Future<void> _loadData() async {
    final data = await apiService.getTrendingStocks();
    setState(() {
      trending = data;
    });
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
        body: SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(24),
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
                        style: Theme.of(context).textTheme.bodyMedium,
                      ),
                      Text(
                        'Abhivishwakarma',
                        style: Theme.of(context).textTheme.displayMedium,
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

              // Portfolio Summary Card
              Container(
                decoration: BoxDecoration(
                  borderRadius: BorderRadius.circular(24),
                  gradient: const LinearGradient(
                    colors: [Color(0xFF1E293B), Color(0xFF0F172A)],
                    begin: Alignment.topLeft,
                    end: Alignment.bottomRight,
                  ),
                  border: Border.all(
                    color: AppTheme.primaryLight.withOpacity(0.5),
                    width: 1.0,
                  ),
                ),
                padding: const EdgeInsets.all(24),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      'Total Portfolio',
                      style: TextStyle(
                        color: Colors.white.withOpacity(0.7),
                        fontSize: 16,
                      ),
                    ),
                    const SizedBox(height: 8),
                    const Text(
                      '₹1,24,592.40',
                      style: TextStyle(
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
                            color: AppTheme.signalBuy.withOpacity(0.15),
                            borderRadius: BorderRadius.circular(10),
                            border: Border.all(color: AppTheme.signalBuy.withOpacity(0.3)),
                          ),
                          child: const Row(
                            children: [
                              Icon(LucideIcons.trendingUp, color: AppTheme.signalBuy, size: 16),
                              SizedBox(width: 6),
                              Text(
                                '+2.4%',
                                style: TextStyle(color: AppTheme.signalBuy, fontWeight: FontWeight.bold),
                              ),
                            ],
                          ),
                        ),
                        const SizedBox(width: 12),
                        Text(
                          'Today',
                          style: TextStyle(color: Colors.white.withOpacity(0.6)),
                        )
                      ],
                    )
                  ],
                ),
              ).animate().fade(delay: 100.ms).slideY(begin: 0.2),

              const SizedBox(height: 32),

              // CTA
              CustomButton(
                text: 'Search a Stock',
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
                style: Theme.of(context).textTheme.titleLarge,
              ).animate().fade(delay: 300.ms),
              const SizedBox(height: 16),

              if (trending.isEmpty)
                const Center(child: CircularProgressIndicator())
              else
                ...trending.map((stock) => Padding(
                      padding: const EdgeInsets.only(bottom: 12),
                      child: PremiumCard(
                        padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 16),
                        child: Builder(
                          builder: (context) {
                            final double price = (stock['price'] ?? 0.0).toDouble();
                            final double changePercent = (stock['changePercent'] ?? stock['change'] ?? 0.0).toDouble();
                            final String? signal = stock['signal']?.toString();
                            
                            return Row(
                          mainAxisAlignment: MainAxisAlignment.spaceBetween,
                          children: [
                            Row(
                              children: [
                                Container(
                                  width: 40,
                                  height: 40,
                                  decoration: BoxDecoration(
                                    color: Colors.white.withOpacity(0.05),
                                    borderRadius: BorderRadius.circular(12),
                                  ),
                                  child: Center(
                                    child: Text(
                                      stock['symbol'].substring(0, 1),
                                      style: const TextStyle(fontWeight: FontWeight.bold),
                                    ),
                                  ),
                                ),
                                const SizedBox(width: 16),
                                Column(
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  children: [
                                    Row(
                                      children: [
                                        Text(
                                          stock['symbol'],
                                          style: const TextStyle(
                                            fontWeight: FontWeight.w600,
                                            fontSize: 16,
                                          ),
                                        ),
                                        const SizedBox(width: 8),
                                        if (signal != null)
                                          Builder(
                                            builder: (context) {
                                              final String signalType = signal.toLowerCase();
                                              Color badgeColor;
                                              if (signalType == 'buy') badgeColor = AppTheme.signalBuy;
                                              else if (signalType == 'avoid') badgeColor = AppTheme.signalAvoid;
                                              else badgeColor = AppTheme.signalNeutral;

                                              return Container(
                                                padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                                                decoration: BoxDecoration(
                                                  color: badgeColor.withOpacity(0.1),
                                                  border: Border.all(
                                                    color: badgeColor,
                                                    width: 1,
                                                  ),
                                                  borderRadius: BorderRadius.circular(6),
                                                ),
                                                child: Text(
                                                  signal.toUpperCase(),
                                                  style: TextStyle(
                                                    color: badgeColor,
                                                    fontSize: 10,
                                                    fontWeight: FontWeight.bold,
                                                  ),
                                                ),
                                              );
                                            }
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
                                  style: const TextStyle(
                                    fontWeight: FontWeight.w600,
                                    fontSize: 16,
                                  ),
                                ),
                                Text(
                                  '${changePercent > 0 ? '+' : ''}$changePercent%',
                                  style: TextStyle(
                                    color: changePercent > 0 ? AppTheme.signalBuy : AppTheme.signalAvoid,
                                    fontWeight: FontWeight.w500,
                                  ),
                                ),
                              ],
                            ),
                          ],
                        );
                      },
                    ),
                  ).animate().fade(delay: 400.ms).slideX(begin: 0.1),
                )),
            ],
          ),
        ),
      ),
    )
    );
  }
}
