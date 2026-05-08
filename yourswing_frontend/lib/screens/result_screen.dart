import 'package:flutter/material.dart';
import 'package:flutter_animate/flutter_animate.dart';
import 'package:lucide_icons/lucide_icons.dart';
import '../theme/app_theme.dart';
import '../widgets/premium_card.dart';
import '../widgets/custom_button.dart';
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
    setState(() => isLoading = true);
    final result = await apiService.fetchStockAnalysis(widget.symbol);
    setState(() {
      data = result;
      isLoading = false;
    });
  }

  // ── Signal helpers ────────────────────────────────────────────
  Color _signalColor(String? signal) {
    final s = (signal ?? '').toLowerCase();
    if (s.contains('strong buy')) return const Color(0xFF00E5A0);
    if (s.contains('buy'))        return const Color(0xFF4ADE80);
    if (s == 'avoid')             return const Color(0xFFFF4D6D);
    return const Color(0xFFFACC15);
  }

  String _signalLabel(String? signal) =>
      (signal ?? 'WATCH').toUpperCase();

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: const BoxDecoration(
        gradient: LinearGradient(
          colors: [
            AppTheme.background,
            AppTheme.backgroundDarker,
          ],
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
          icon: const Icon(LucideIcons.arrowLeft, color: Colors.white),
          onPressed: () => Navigator.pop(context),
        ),
        title: Text(
          widget.symbol.toUpperCase(),
          style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold),
        ),
        actions: [
          IconButton(
            icon: const Icon(LucideIcons.star, color: Colors.white54),
            onPressed: () {},
          ),
        ],
      ),
      body: isLoading
          ? const Center(
              child: CircularProgressIndicator(
                color: Color(0xFF4F8EF7),
                strokeWidth: 2,
              ),
            )
          : data == null
              ? _buildErrorState()
              : SafeArea(
                  child: RefreshIndicator(
                    onRefresh: _fetchData,
                    color: const Color(0xFF4F8EF7),
                    backgroundColor: const Color(0xFF111827),
                    child: CustomScrollView(
                      physics: const AlwaysScrollableScrollPhysics(),
                      slivers: [
                        // ── Price Card ──────────────────────────────
                        SliverToBoxAdapter(
                          child: Padding(
                            padding: const EdgeInsets.fromLTRB(24, 12, 24, 0),
                            child: _buildPriceCard(),
                          ),
                        ),

                        // ── Signal Section ──────────────────────────
                        SliverToBoxAdapter(
                          child: Padding(
                            padding: const EdgeInsets.fromLTRB(24, 24, 24, 0),
                            child: _buildSignalCard(),
                          ),
                        ),

                        // ── Indicators Section ───────────────────────
                        SliverToBoxAdapter(
                          child: Padding(
                            padding: const EdgeInsets.fromLTRB(24, 32, 24, 32),
                            child: Container(
                              decoration: BoxDecoration(
                                color: const Color(0xFF111827),
                                borderRadius: BorderRadius.circular(20),
                                border: Border.all(color: Colors.white.withOpacity(0.05)),
                              ),
                              padding: const EdgeInsets.all(20),
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Row(
                                    children: [
                                      const Text(
                                        'Technical Indicators',
                                        style: TextStyle(
                                          color: Colors.white,
                                          fontSize: 18,
                                          fontWeight: FontWeight.w700,
                                          letterSpacing: -0.3,
                                        ),
                                      ),
                                      const SizedBox(width: 8),
                                      Icon(
                                        LucideIcons.info,
                                        size: 16,
                                        color: Colors.white.withOpacity(0.3),
                                      ),
                                    ],
                                  ),
                                  const SizedBox(height: 20),
                                  GridView.count(
                                    crossAxisCount: 2,
                                    crossAxisSpacing: 12,
                                    mainAxisSpacing: 12,
                                    childAspectRatio: 2.2,
                                    shrinkWrap: true,
                                    physics: const NeverScrollableScrollPhysics(),
                                    children: [
                                      _buildIndicatorTile('RSI (14)', '${data!['indicators']['RSI']['value']}'),
                                      _buildIndicatorTile('EMA (20)', '₹${data!['indicators']['EMA20']['value']}'),
                                      _buildIndicatorTile('EMA (50)', '₹${data!['indicators']['EMA50']['value']}'),
                                      _buildIndicatorTile('MACD', '${data!['macd']}'),
                                      _buildIndicatorTile('ATR', '₹${data!['atr']}'),
                                      _buildIndicatorTile('Volume Ratio', '${data!['volume_ratio']}x'),
                                      _buildIndicatorTile('Rel. Strength', '${data!['relative_strength']}'),
                                      _buildIndicatorTile('Breakout', data!['breakout'] == true ? 'YES' : 'NO'),
                                    ],
                                  ),
                                ],
                              ),
                            ),
                          ),
                        ),
                      ],
                    ),
                  ),
                ),
      ),
    );
  }

  Widget _buildPriceCard() {
    final isUp = data!['change'] >= 0;
    return Container(
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(24),
        gradient: const LinearGradient(
          colors: [Color(0xFF1A2744), Color(0xFF0D1526)],
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
        ),
        border: Border.all(
          color: const Color(0xFF4F8EF7).withOpacity(0.25),
          width: 1,
        ),
      ),
      padding: const EdgeInsets.all(24),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            data!['symbol'],
            style: TextStyle(
              color: Colors.white.withOpacity(0.5),
              fontSize: 13,
              fontWeight: FontWeight.w500,
            ),
          ),
          const SizedBox(height: 8),
          Row(
            crossAxisAlignment: CrossAxisAlignment.end,
            children: [
              Text(
                '₹${data!['price']}',
                style: const TextStyle(
                  color: Colors.white,
                  fontSize: 36,
                  fontWeight: FontWeight.w800,
                  letterSpacing: -1.5,
                ),
              ),
              const SizedBox(width: 12),
              Padding(
                padding: const EdgeInsets.only(bottom: 6),
                child: Container(
                  padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                  decoration: BoxDecoration(
                    color: (isUp ? const Color(0xFF4ADE80) : const Color(0xFFFF4D6D)).withOpacity(0.1),
                    borderRadius: BorderRadius.circular(8),
                  ),
                  child: Text(
                    '${isUp ? '+' : '-'}₹${data!['change'].abs().toStringAsFixed(2)} (${data!['changePercent'].toStringAsFixed(1)}%)',
                    style: TextStyle(
                      color: isUp ? const Color(0xFF4ADE80) : const Color(0xFFFF4D6D),
                      fontSize: 12,
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                ),
              ),
            ],
          ),
        ],
      ),
    ).animate().fade().slideY(begin: 0.1);
  }

  Widget _buildSignalCard() {
    final signal = data!['signal'];
    final score = (data!['score'] ?? 0.0).toDouble();
    final color = _signalColor(signal);

    return Container(
      decoration: BoxDecoration(
        color: const Color(0xFF111827),
        borderRadius: BorderRadius.circular(24),
        border: Border.all(color: const Color(0xFF1F2937)),
      ),
      padding: const EdgeInsets.all(20),
      child: Row(
        children: [
          _ScoreRing(score: score, color: color, size: 64),
          const SizedBox(width: 20),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  'Overall Signal',
                  style: TextStyle(
                    color: Colors.white.withOpacity(0.4),
                    fontSize: 12,
                    fontWeight: FontWeight.w500,
                  ),
                ),
                const SizedBox(height: 4),
                Text(
                  _signalLabel(signal),
                  style: TextStyle(
                    color: color,
                    fontSize: 24,
                    fontWeight: FontWeight.w800,
                    letterSpacing: 0.5,
                  ),
                ),
                const SizedBox(height: 2),
                Text(
                  'Signal Accuracy: ${score.toInt()}%',
                  style: TextStyle(
                    color: Colors.white.withOpacity(0.3),
                    fontSize: 11,
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    ).animate().fade(delay: 100.ms).slideY(begin: 0.1);
  }

  Widget _buildIndicatorTile(String title, String value) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
      decoration: BoxDecoration(
        color: const Color(0xFF1E293B).withOpacity(0.3),
        borderRadius: BorderRadius.circular(12),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Text(
            title,
            style: TextStyle(
              color: Colors.white.withOpacity(0.4),
              fontSize: 12,
              fontWeight: FontWeight.w500,
            ),
          ),
          const SizedBox(height: 4),
          Text(
            value,
            style: const TextStyle(
              color: Colors.white,
              fontSize: 16,
              fontWeight: FontWeight.w700,
              letterSpacing: -0.2,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildErrorState() {
    return Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          const Icon(LucideIcons.alertTriangle, size: 48, color: Color(0xFFFF4D6D)),
          const SizedBox(height: 16),
          const Text(
            'Failed to load analysis',
            style: TextStyle(color: Colors.white, fontSize: 16),
          ),
          const SizedBox(height: 24),
          ElevatedButton(
            onPressed: _fetchData,
            style: ElevatedButton.styleFrom(backgroundColor: const Color(0xFF4F8EF7)),
            child: const Text('Try Again'),
          ),
        ],
      ),
    );
  }
}

class _ScoreRing extends StatelessWidget {
  final double score;
  final Color color;
  final double size;

  const _ScoreRing({
    required this.score,
    required this.color,
    required this.size,
  });

  @override
  Widget build(BuildContext context) {
    final double value = (score / 100.0).clamp(0.0, 1.0);
    const double stroke = 4.0;
    const double innerPad = 4.0;
    final double textArea = size - 2 * stroke - 2 * innerPad;

    return SizedBox(
      width: size,
      height: size,
      child: Stack(
        alignment: Alignment.center,
        children: [
          SizedBox(
            width: size,
            height: size,
            child: CircularProgressIndicator(
              value: 1.0,
              color: Colors.white.withOpacity(0.06),
              strokeWidth: stroke,
              strokeCap: StrokeCap.round,
            ),
          ),
          SizedBox(
            width: size,
            height: size,
            child: CircularProgressIndicator(
              value: value,
              color: color,
              strokeWidth: stroke,
              strokeCap: StrokeCap.round,
            ),
          ),
          SizedBox(
            width: textArea,
            height: textArea,
            child: Center(
              child: FittedBox(
                fit: BoxFit.scaleDown,
                child: Text(
                  '${score.toInt()}%',
                  style: const TextStyle(
                    color: Colors.white,
                    fontWeight: FontWeight.w800,
                    fontSize: 22, // Base size, FittedBox will scale it
                    height: 1,
                  ),
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }
}