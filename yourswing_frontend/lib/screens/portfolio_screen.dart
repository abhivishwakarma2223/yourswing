import 'package:flutter/material.dart';
import 'package:lucide_icons/lucide_icons.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:provider/provider.dart';
import '../models/portfolio_item.dart';
import '../services/api_service.dart';
import '../theme/app_theme.dart';
import '../providers/portfolio_provider.dart';
import 'search_screen.dart';

class PortfolioScreen extends StatefulWidget {
  const PortfolioScreen({super.key});

  @override
  State<PortfolioScreen> createState() => _PortfolioScreenState();
}

class _PortfolioScreenState extends State<PortfolioScreen> {
  @override
  void initState() {
    super.initState();
    // Portfolio loading is handled by the Provider
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
          decoration: BoxDecoration(
            color: const Color(0xFF0D1526),
            borderRadius: const BorderRadius.vertical(top: Radius.circular(32)),
            border: Border.all(color: Colors.white.withOpacity(0.08)),
          ),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // drag handle
              Center(
                child: Container(
                  width: 40,
                  height: 4,
                  margin: const EdgeInsets.only(bottom: 24),
                  decoration: BoxDecoration(
                    color: Colors.white.withOpacity(0.15),
                    borderRadius: BorderRadius.circular(2),
                  ),
                ),
              ),
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        item == null ? 'Add Stock' : 'Edit Holding',
                        style: GoogleFonts.outfit(
                          color: Colors.white,
                          fontSize: 22,
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                      Text(
                        item == null ? 'Track a new position' : 'Update your position',
                        style: GoogleFonts.outfit(
                          color: Colors.white38,
                          fontSize: 13,
                        ),
                      ),
                    ],
                  ),
                  GestureDetector(
                    onTap: () => Navigator.pop(context),
                    child: Container(
                      width: 36,
                      height: 36,
                      decoration: BoxDecoration(
                        color: Colors.white.withOpacity(0.06),
                        borderRadius: BorderRadius.circular(10),
                      ),
                      child: const Icon(LucideIcons.x, color: Colors.white38, size: 18),
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 28),
              _buildTextField(symbolController, 'STOCK SYMBOL', 'e.g. RELIANCE'),
              const SizedBox(height: 16),
              Row(
                children: [
                  Expanded(child: _buildTextField(qtyController, 'QUANTITY', 'e.g. 10', isNumeric: true)),
                  const SizedBox(width: 14),
                  Expanded(child: _buildTextField(priceController, 'AVG. BUY PRICE', '₹0.00', isNumeric: true)),
                ],
              ),
              const SizedBox(height: 32),
              SizedBox(
                width: double.infinity,
                height: 54,
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

                    // Save via Provider
                    final provider = context.read<PortfolioProvider>();
                    await provider.saveStock(newItem);
                    if (mounted) Navigator.pop(context);
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
        Text(
          label,
          style: GoogleFonts.outfit(
            color: Colors.white.withOpacity(0.35),
            fontSize: 10,
            fontWeight: FontWeight.bold,
            letterSpacing: 1.2,
          ),
        ),
        const SizedBox(height: 8),
        TextField(
          controller: controller,
          keyboardType: isNumeric ? TextInputType.number : TextInputType.text,
          style: GoogleFonts.outfit(color: Colors.white, fontSize: 15),
          decoration: InputDecoration(
            hintText: hint,
            hintStyle: TextStyle(color: Colors.white.withOpacity(0.1)),
            filled: true,
            fillColor: Colors.white.withOpacity(0.04),
            contentPadding: const EdgeInsets.symmetric(horizontal: 18, vertical: 16),
            border: OutlineInputBorder(
              borderRadius: BorderRadius.circular(14),
              borderSide: BorderSide(color: Colors.white.withOpacity(0.07)),
            ),
            enabledBorder: OutlineInputBorder(
              borderRadius: BorderRadius.circular(14),
              borderSide: BorderSide(color: Colors.white.withOpacity(0.07)),
            ),
            focusedBorder: OutlineInputBorder(
              borderRadius: BorderRadius.circular(14),
              borderSide: const BorderSide(color: AppTheme.primaryLight, width: 1.5),
            ),
          ),
        ),
      ],
    );
  }

  // ── Summary numbers ─────────────────────────────────────────────────────────
  // Summary logic moved to PortfolioProvider

  @override
  Widget build(BuildContext context) {
    return Consumer<PortfolioProvider>(
      builder: (context, portfolio, child) {
        final holdings = portfolio.holdings;
        
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
              toolbarHeight: 64,
              title: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    'My Portfolio',
                    style: GoogleFonts.outfit(
                      color: Colors.white,
                      fontWeight: FontWeight.bold,
                      fontSize: 22,
                    ),
                  ),
                  Text(
                    '${holdings.length} holding${holdings.length == 1 ? '' : 's'}',
                    style: GoogleFonts.outfit(
                      color: Colors.white38,
                      fontSize: 12,
                    ),
                  ),
                ],
              ),
              actions: [
                _buildIconBtn(LucideIcons.refreshCw, portfolio.loadPortfolio),
                const SizedBox(width: 12),
              ],
            ),
            body: portfolio.isLoading
                ? _buildLoadingState()
                : holdings.isEmpty
                    ? _buildEmptyState()
                    : _buildBody(portfolio),
            floatingActionButton: _buildFAB(),
          ),
        );
      },
    );
  }

  Widget _buildIconBtn(IconData icon, VoidCallback onTap) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        width: 38,
        height: 38,
        decoration: BoxDecoration(
          color: Colors.white.withOpacity(0.06),
          borderRadius: BorderRadius.circular(12),
          border: Border.all(color: Colors.white.withOpacity(0.08)),
        ),
        child: Icon(icon, color: Colors.white54, size: 18),
      ),
    );
  }

  Widget _buildFAB() {
    return Container(
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(18),
        boxShadow: [
          BoxShadow(
            color: AppTheme.primaryLight.withOpacity(0.35),
            blurRadius: 20,
            spreadRadius: 0,
            offset: const Offset(0, 6),
          ),
        ],
      ),
      child: FloatingActionButton(
        backgroundColor: AppTheme.primaryLight,
        elevation: 0,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(18)),
        onPressed: () => _showAddEditModal(),
        child: const Icon(LucideIcons.plus, color: Colors.black, size: 24),
      ),
    );
  }

  Widget _buildLoadingState() {
    return Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          const CircularProgressIndicator(
            color: AppTheme.primaryLight,
            strokeWidth: 2,
          ),
          const SizedBox(height: 16),
          Text(
            'Fetching live prices…',
            style: GoogleFonts.outfit(color: Colors.white24, fontSize: 13),
          ),
        ],
      ),
    );
  }

  Widget _buildBody(PortfolioProvider portfolio) {
    final holdings = portfolio.holdings;
    final livePrices = portfolio.livePrices;
    final summary = portfolio.getSummary();
    final isOverallProfit = (summary['pnl'] ?? 0) >= 0;

    return CustomScrollView(
      slivers: [
        SliverToBoxAdapter(
          child: Padding(
            padding: const EdgeInsets.fromLTRB(20, 4, 20, 8),
            child: _buildSummaryCard(summary, isOverallProfit),
          ),
        ),
        SliverPadding(
          padding: const EdgeInsets.fromLTRB(20, 8, 20, 100),
          sliver: SliverList(
            delegate: SliverChildBuilderDelegate(
              (context, index) => _buildHoldingTile(holdings[index], livePrices),
              childCount: holdings.length,
            ),
          ),
        ),
      ],
    );
  }

  Widget _buildSummaryCard(Map<String, double> summary, bool isOverallProfit) {
    final pnl = summary['pnl'] ?? 0;
    final pnlPct = summary['pnlPct'] ?? 0;
    final current = summary['current'] ?? 0;
    final invested = summary['invested'] ?? 0;
    final pnlColor = isOverallProfit ? AppTheme.signalBuy : AppTheme.signalAvoid;

    return Container(
      margin: const EdgeInsets.only(bottom: 8),
      padding: const EdgeInsets.all(22),
      decoration: BoxDecoration(
        gradient: LinearGradient(
          colors: [
            const Color(0xFF1A2744),
            const Color(0xFF0F1B35),
          ],
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
        ),
        borderRadius: BorderRadius.circular(24),
        border: Border.all(color: Colors.white.withOpacity(0.07)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text(
                'Current Value',
                style: GoogleFonts.outfit(color: Colors.white38, fontSize: 12, letterSpacing: 0.3),
              ),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                decoration: BoxDecoration(
                  color: pnlColor.withOpacity(0.12),
                  borderRadius: BorderRadius.circular(8),
                ),
                child: Row(
                  children: [
                    Icon(
                      isOverallProfit ? LucideIcons.trendingUp : LucideIcons.trendingDown,
                      color: pnlColor,
                      size: 13,
                    ),
                    const SizedBox(width: 4),
                    Text(
                      '${isOverallProfit ? '+' : ''}${pnlPct.toStringAsFixed(2)}%',
                      style: GoogleFonts.outfit(
                        color: pnlColor,
                        fontSize: 12,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ),
          const SizedBox(height: 6),
          Text(
            '₹${current.toStringAsFixed(2)}',
            style: GoogleFonts.outfit(
              color: Colors.white,
              fontSize: 30,
              fontWeight: FontWeight.bold,
              letterSpacing: -0.5,
            ),
          ),
          const SizedBox(height: 16),
          Container(height: 1, color: Colors.white.withOpacity(0.05)),
          const SizedBox(height: 14),
          Row(
            children: [
              Expanded(
                child: _buildSummaryItem(
                  'Invested',
                  '₹${invested.toStringAsFixed(2)}',
                  Colors.white54,
                ),
              ),
              Container(width: 1, height: 32, color: Colors.white.withOpacity(0.07)),
              Expanded(
                child: _buildSummaryItem(
                  'Total P&L',
                  '${isOverallProfit ? '+' : ''}₹${pnl.abs().toStringAsFixed(2)}',
                  pnlColor,
                  align: TextAlign.right,
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildSummaryItem(String label, String value, Color valueColor, {TextAlign align = TextAlign.left}) {
    return Column(
      crossAxisAlignment: align == TextAlign.right ? CrossAxisAlignment.end : CrossAxisAlignment.start,
      children: [
        Text(
          label,
          style: GoogleFonts.outfit(color: Colors.white24, fontSize: 11, letterSpacing: 0.2),
        ),
        const SizedBox(height: 3),
        Text(
          value,
          style: GoogleFonts.outfit(
            color: valueColor,
            fontSize: 15,
            fontWeight: FontWeight.w700,
          ),
        ),
      ],
    );
  }

  Widget _buildHoldingTile(PortfolioItem item, Map<String, Map<String, double>> liveData) {
    // ── Logic untouched ──────────────────────────────────────────────────────
    String lookupSymbol = item.symbol.toUpperCase();
    if (!lookupSymbol.contains('.')) lookupSymbol = '$lookupSymbol.NS';

    final stockData = liveData[lookupSymbol];
    double currentPrice = item.averagePrice;
    double dailyChangePrice = 0.0;
    double dailyChangePercent = 0.0;

    bool hasLivePrice = stockData != null && (stockData['price'] ?? 0) > 0;
    bool isStale = !hasLivePrice;

    if (hasLivePrice) {
      currentPrice = stockData['price']!;
      dailyChangePrice = (stockData['change'] ?? 0.0) * item.quantity;
      dailyChangePercent = stockData['changePercent'] ?? 0.0;
    } else {
      // Fallback: If no live price, use average price as current to show 0% change
      currentPrice = item.averagePrice;
    }

    double totalPnl = (currentPrice - item.averagePrice) * item.quantity;
    double totalPnlPercent = item.averagePrice > 0
        ? ((currentPrice - item.averagePrice) / item.averagePrice) * 100
        : 0.0;

    bool isProfit = totalPnl >= 0;
    bool isDailyUp = dailyChangePrice >= 0;
    // ────────────────────────────────────────────────────────────────────────

    final pnlColor = isProfit ? AppTheme.signalBuy : AppTheme.signalAvoid;
    final dailyColor = isDailyUp ? AppTheme.signalBuy : AppTheme.signalAvoid;

    // strip .NS for display
    final displaySymbol = item.symbol.replaceAll('.NS', '').replaceAll('.ns', '');

    return Container(
      margin: const EdgeInsets.only(bottom: 14),
      decoration: BoxDecoration(
        color: const Color(0xFF111827),
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: Colors.white.withOpacity(0.06)),
      ),
      child: Column(
        children: [
          // ── Top row ────────────────────────────────────────────────────────
          Padding(
            padding: const EdgeInsets.fromLTRB(16, 16, 12, 14),
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                // Icon badge
                Container(
                  width: 46,
                  height: 46,
                  decoration: BoxDecoration(
                    gradient: LinearGradient(
                      colors: [
                        AppTheme.primaryLight.withOpacity(0.18),
                        AppTheme.primaryLight.withOpacity(0.05),
                      ],
                      begin: Alignment.topLeft,
                      end: Alignment.bottomRight,
                    ),
                    borderRadius: BorderRadius.circular(14),
                    border: Border.all(color: AppTheme.primaryLight.withOpacity(0.15)),
                  ),
                  child: Center(
                    child: Text(
                      displaySymbol.isNotEmpty ? displaySymbol[0] : '?',
                      style: GoogleFonts.outfit(
                        color: AppTheme.primaryLight,
                        fontWeight: FontWeight.bold,
                        fontSize: 18,
                      ),
                    ),
                  ),
                ),
                const SizedBox(width: 14),

                // Symbol + qty
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        children: [
                          Text(
                            displaySymbol,
                            style: GoogleFonts.outfit(
                              color: Colors.white,
                              fontWeight: FontWeight.bold,
                              fontSize: 16,
                            ),
                          ),
                          const SizedBox(width: 6),
                          if (hasLivePrice)
                            Container(
                              padding: const EdgeInsets.symmetric(horizontal: 5, vertical: 1.5),
                              decoration: BoxDecoration(
                                color: AppTheme.signalBuy.withOpacity(0.1),
                                borderRadius: BorderRadius.circular(4),
                                border: Border.all(color: AppTheme.signalBuy.withOpacity(0.2), width: 0.5),
                              ),
                              child: Text(
                                'LIVE',
                                style: GoogleFonts.outfit(
                                  color: AppTheme.signalBuy,
                                  fontSize: 7,
                                  fontWeight: FontWeight.w900,
                                  letterSpacing: 0.5,
                                ),
                              ),
                            )
                          else
                            Container(
                              padding: const EdgeInsets.symmetric(horizontal: 5, vertical: 1.5),
                              decoration: BoxDecoration(
                                color: Colors.white.withOpacity(0.05),
                                borderRadius: BorderRadius.circular(4),
                              ),
                              child: Text(
                                'OFFLINE',
                                style: GoogleFonts.outfit(
                                  color: Colors.white.withOpacity(0.2),
                                  fontSize: 7,
                                  fontWeight: FontWeight.bold,
                                ),
                              ),
                            ),
                        ],
                      ),
                      const SizedBox(height: 2),
                      Text(
                        '${item.quantity.toInt()} shares  ·  avg ₹${item.averagePrice.toStringAsFixed(2)}',
                        style: GoogleFonts.outfit(color: Colors.white38, fontSize: 11.5),
                      ),
                    ],
                  ),
                ),

                // Live price
                Column(
                  crossAxisAlignment: CrossAxisAlignment.end,
                  children: [
                    Text(
                      '₹${currentPrice.toStringAsFixed(2)}',
                      style: GoogleFonts.outfit(
                        color: Colors.white,
                        fontWeight: FontWeight.bold,
                        fontSize: 15,
                      ),
                    ),
                    const SizedBox(height: 2),
                    Row(
                      children: [
                        Icon(
                          isDailyUp ? LucideIcons.arrowUpRight : LucideIcons.arrowDownRight,
                          color: dailyColor,
                          size: 12,
                        ),
                        Text(
                          '${dailyChangePercent.abs().toStringAsFixed(2)}%',
                          style: GoogleFonts.outfit(
                            color: dailyColor,
                            fontSize: 11,
                            fontWeight: FontWeight.w600,
                          ),
                        ),
                      ],
                    ),
                  ],
                ),
                const SizedBox(width: 4),

                // Menu
                PopupMenuButton<String>(
                  icon: Icon(LucideIcons.moreVertical, color: Colors.white24, size: 18),
                  padding: EdgeInsets.zero,
                  constraints: const BoxConstraints(),
                  color: const Color(0xFF1E293B),
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                  onSelected: (value) async {
                    if (value == 'edit') {
                      _showAddEditModal(item: item);
                    } else if (value == 'delete') {
                      context.read<PortfolioProvider>().deleteStock(item.symbol);
                    }
                  },
                  itemBuilder: (context) => [
                    PopupMenuItem(
                      value: 'edit',
                      child: Row(
                        children: [
                          Icon(LucideIcons.pencil, size: 15, color: Colors.white70),
                          const SizedBox(width: 8),
                          Text('Edit', style: GoogleFonts.outfit(color: Colors.white70)),
                        ],
                      ),
                    ),
                    PopupMenuItem(
                      value: 'delete',
                      child: Row(
                        children: [
                          Icon(LucideIcons.trash2, size: 15, color: AppTheme.signalAvoid),
                          const SizedBox(width: 8),
                          Text('Delete', style: GoogleFonts.outfit(color: AppTheme.signalAvoid)),
                        ],
                      ),
                    ),
                  ],
                ),
              ],
            ),
          ),

          // ── Bottom stats row ───────────────────────────────────────────────
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
            decoration: BoxDecoration(
              color: Colors.white.withOpacity(0.02),
              borderRadius: const BorderRadius.vertical(bottom: Radius.circular(20)),
              border: Border(top: BorderSide(color: Colors.white.withOpacity(0.04))),
            ),
            child: Row(
              children: [
                // P&L pill
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        'TOTAL P&L',
                        style: GoogleFonts.outfit(
                          color: Colors.white24,
                          fontSize: 9.5,
                          fontWeight: FontWeight.bold,
                          letterSpacing: 0.8,
                        ),
                      ),
                      const SizedBox(height: 4),
                      Container(
                        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                        decoration: BoxDecoration(
                          color: pnlColor.withOpacity(0.1),
                          borderRadius: BorderRadius.circular(8),
                        ),
                        child: Text(
                          '${isProfit ? '+' : '-'}₹${totalPnl.abs().toStringAsFixed(2)}  (${totalPnlPercent.abs().toStringAsFixed(2)}%)',
                          style: GoogleFonts.outfit(
                            color: pnlColor,
                            fontSize: 12.5,
                            fontWeight: FontWeight.bold,
                          ),
                        ),
                      ),
                    ],
                  ),
                ),

                // Today pill
                Column(
                  crossAxisAlignment: CrossAxisAlignment.end,
                  children: [
                    Text(
                      'TODAY',
                      style: GoogleFonts.outfit(
                        color: Colors.white24,
                        fontSize: 9.5,
                        fontWeight: FontWeight.bold,
                        letterSpacing: 0.8,
                      ),
                    ),
                    const SizedBox(height: 4),
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                      decoration: BoxDecoration(
                        color: dailyColor.withOpacity(0.1),
                        borderRadius: BorderRadius.circular(8),
                      ),
                      child: Text(
                        '${isDailyUp ? '+' : '-'}₹${dailyChangePrice.abs().toStringAsFixed(2)}  (${dailyChangePercent.abs().toStringAsFixed(2)}%)',
                        style: GoogleFonts.outfit(
                          color: dailyColor,
                          fontSize: 12.5,
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                    ),
                  ],
                ),
              ],
            ),
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
          Container(
            width: 90,
            height: 90,
            decoration: BoxDecoration(
              color: AppTheme.primaryLight.withOpacity(0.06),
              shape: BoxShape.circle,
              border: Border.all(color: AppTheme.primaryLight.withOpacity(0.12), width: 1.5),
            ),
            child: Icon(LucideIcons.layoutList, size: 38, color: AppTheme.primaryLight.withOpacity(0.3)),
          ),
          const SizedBox(height: 24),
          Text(
            'No holdings yet',
            style: GoogleFonts.outfit(
              color: Colors.white.withOpacity(0.55),
              fontSize: 19,
              fontWeight: FontWeight.w600,
            ),
          ),
          const SizedBox(height: 8),
          Text(
            'Tap  +  to add your first stock',
            style: GoogleFonts.outfit(
              color: Colors.white.withOpacity(0.2),
              fontSize: 13.5,
            ),
          ),
          const SizedBox(height: 36),
          GestureDetector(
            onTap: () => _showAddEditModal(),
            child: Container(
              padding: const EdgeInsets.symmetric(horizontal: 28, vertical: 14),
              decoration: BoxDecoration(
                color: AppTheme.primaryLight.withOpacity(0.12),
                borderRadius: BorderRadius.circular(14),
                border: Border.all(color: AppTheme.primaryLight.withOpacity(0.25)),
              ),
              child: Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Icon(LucideIcons.plus, color: AppTheme.primaryLight, size: 18),
                  const SizedBox(width: 8),
                  Text(
                    'Add Stock',
                    style: GoogleFonts.outfit(
                      color: AppTheme.primaryLight,
                      fontWeight: FontWeight.w600,
                      fontSize: 14,
                    ),
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }
}
