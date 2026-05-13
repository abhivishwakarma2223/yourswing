import 'package:flutter/material.dart';
import 'package:flutter_animate/flutter_animate.dart';
import 'package:lucide_icons/lucide_icons.dart';
import 'package:google_fonts/google_fonts.dart';
import '../theme/app_theme.dart';
import '../widgets/premium_card.dart';
import '../widgets/custom_button.dart';
import '../services/api_service.dart';

// ─── helpers ─────────────────────────────────────────────────
double _d(dynamic v, {double def = 0.0}) {
  if (v == null) return def;
  if (v is double) return v;
  if (v is int) return v.toDouble();
  return def;
}

Color _signalColor(String sig) {
  if (sig.contains('BUY')) return AppTheme.signalBuy;
  if (sig == 'AVOID') return AppTheme.signalAvoid;
  return AppTheme.signalNeutral;
}

// ─── Screen ──────────────────────────────────────────────────
class ResultScreen extends StatefulWidget {
  final String symbol;
  const ResultScreen({super.key, required this.symbol});

  @override
  State<ResultScreen> createState() => _ResultScreenState();
}

class _ResultScreenState extends State<ResultScreen> {
  Map<String, dynamic>? data;
  bool isLoading = true;
  String? error;

  @override
  void initState() {
    super.initState();
    _fetch();
  }

  Future<void> _fetch() async {
    setState(() { isLoading = true; error = null; });
    try {
      final result = await apiService.fetchStockAnalysis(widget.symbol);
      setState(() { data = result; isLoading = false; });
    } catch (e) {
      setState(() { error = e.toString(); isLoading = false; });
    }
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
          leading: IconButton(
            icon: const Icon(LucideIcons.chevronLeft, color: Colors.white),
            onPressed: () => Navigator.pop(context),
          ),
          title: Text(
            widget.symbol.replaceAll('.NS', '').replaceAll('.BO', ''),
            style: GoogleFonts.outfit(
              color: Colors.white,
              fontWeight: FontWeight.bold,
              fontSize: 20,
              letterSpacing: -0.3,
            ),
          ),
          actions: [
            IconButton(
              icon: Icon(LucideIcons.refreshCw, color: Colors.white.withOpacity(0.5), size: 18),
              onPressed: _fetch,
            ),
            const SizedBox(width: 8),
          ],
        ),
        body: isLoading
            ? _buildLoading()
            : error != null || data == null
                ? _buildError()
                : _buildBody(),
      ),
    );
  }

  Widget _buildLoading() {
    return Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          const SizedBox(
            width: 44,
            height: 44,
            child: CircularProgressIndicator(
              color: AppTheme.primaryLight,
              strokeWidth: 2.5,
            ),
          ).animate(onPlay: (c) => c.repeat()).rotate(duration: 2.seconds),
          const SizedBox(height: 20),
          Text(
            'Analysing ${widget.symbol.replaceAll('.NS', '')}...',
            style: GoogleFonts.outfit(
              color: AppTheme.textMuted,
              fontSize: 14,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildError() {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(32),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Container(
              padding: const EdgeInsets.all(20),
              decoration: BoxDecoration(
                color: AppTheme.signalAvoid.withOpacity(0.1),
                shape: BoxShape.circle,
                border: Border.all(color: AppTheme.signalAvoid.withOpacity(0.2)),
              ),
              child: const Icon(LucideIcons.alertCircle, color: AppTheme.signalAvoid, size: 36),
            ),
            const SizedBox(height: 24),
            Text('Analysis Failed', style: GoogleFonts.outfit(color: Colors.white, fontSize: 22, fontWeight: FontWeight.bold)),
            const SizedBox(height: 8),
            Text(
              'Could not load data for ${widget.symbol}',
              style: GoogleFonts.outfit(color: AppTheme.textMuted, fontSize: 14),
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: 32),
            CustomButton(text: 'Retry', onPressed: _fetch),
          ],
        ),
      ),
    );
  }

  Widget _buildBody() {
    final d = data!;
    return RefreshIndicator(
      onRefresh: _fetch,
      color: AppTheme.primaryLight,
      backgroundColor: const Color(0xFF111827),
      child: SingleChildScrollView(
        padding: const EdgeInsets.fromLTRB(24, 8, 24, 40),
        physics: const AlwaysScrollableScrollPhysics(),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            _HeroCard(data: d).animate().fade().slideY(begin: 0.2, curve: Curves.easeOutQuad),
            const SizedBox(height: 20),
            _ExecutionCard(data: d).animate().fade(delay: 100.ms).slideY(begin: 0.2, curve: Curves.easeOutQuad),
            const SizedBox(height: 20),
            _RegimeCard(data: d).animate().fade(delay: 150.ms).slideY(begin: 0.2, curve: Curves.easeOutQuad),
            const SizedBox(height: 24),
            Text('Scoring Breakdown', style: GoogleFonts.outfit(color: Colors.white, fontSize: 18, fontWeight: FontWeight.bold))
                .animate().fade(delay: 200.ms),
            const SizedBox(height: 12),
            _ComponentsCard(data: d).animate().fade(delay: 250.ms).slideY(begin: 0.2, curve: Curves.easeOutQuad),
            const SizedBox(height: 24),
            Text('Signal Matrix', style: GoogleFonts.outfit(color: Colors.white, fontSize: 18, fontWeight: FontWeight.bold))
                .animate().fade(delay: 300.ms),
            const SizedBox(height: 12),
            _SignalMatrixCard(data: d).animate().fade(delay: 350.ms).slideY(begin: 0.2, curve: Curves.easeOutQuad),
          ],
        ),
      ),
    );
  }
}

// ─── Hero Card ───────────────────────────────────────────────
class _HeroCard extends StatelessWidget {
  final Map<String, dynamic> data;
  const _HeroCard({required this.data});

  @override
  Widget build(BuildContext context) {
    final Map<String, dynamic> ui = data['ui_data'] is Map ? data['ui_data'] : {};
    final double score = _d(data['score']);
    final String signal = (data['signal']?.toString() ?? 'WATCH').toUpperCase();
    final double change = _d(data['change']);
    final double changePercent = _d(data['changePercent']);
    final bool isUp = change >= 0;
    final Color sigColor = _signalColor(signal);
    final String grade = ui['confidence_grade']?.toString() ?? 'C';
    final String setupType = ui['setup_type']?.toString() ?? 'WATCH';

    return Container(
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(28),
        gradient: LinearGradient(
          colors: [const Color(0xFF1E293B), const Color(0xFF0F172A).withOpacity(0.8)],
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
        ),
        border: Border.all(color: Colors.white.withOpacity(0.08), width: 1.5),
        boxShadow: [
          BoxShadow(color: Colors.black.withOpacity(0.4), blurRadius: 24, offset: const Offset(0, 12)),
          BoxShadow(color: sigColor.withOpacity(0.06), blurRadius: 40, spreadRadius: -10),
        ],
      ),
      clipBehavior: Clip.antiAlias,
      child: Stack(
        children: [
          // decorative orb
          Positioned(
            right: -40,
            top: -40,
            child: Container(
              width: 160,
              height: 160,
              decoration: BoxDecoration(
                color: sigColor.withOpacity(0.04),
                shape: BoxShape.circle,
              ),
            ),
          ),
          Padding(
            padding: const EdgeInsets.all(28),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                // Row 1: price + score ring
                Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            '₹${_d(data['price']).toStringAsFixed(2)}',
                            style: GoogleFonts.outfit(
                              color: Colors.white,
                              fontSize: 38,
                              fontWeight: FontWeight.bold,
                              letterSpacing: -1,
                            ),
                          ),
                          const SizedBox(height: 6),
                          Row(
                            children: [
                              Icon(
                                isUp ? LucideIcons.trendingUp : LucideIcons.trendingDown,
                                color: isUp ? AppTheme.signalBuy : AppTheme.signalAvoid,
                                size: 15,
                              ),
                              const SizedBox(width: 6),
                              Text(
                                '${isUp ? '+' : ''}${change.toStringAsFixed(2)} (${changePercent.toStringAsFixed(2)}%)',
                                style: GoogleFonts.outfit(
                                  color: isUp ? AppTheme.signalBuy : AppTheme.signalAvoid,
                                  fontWeight: FontWeight.w600,
                                  fontSize: 14,
                                ),
                              ),
                            ],
                          ),
                        ],
                      ),
                    ),
                    // Score ring
                    Stack(
                      alignment: Alignment.center,
                      children: [
                        SizedBox(
                          width: 72,
                          height: 72,
                          child: CircularProgressIndicator(
                            value: score / 100.0,
                            backgroundColor: Colors.white.withOpacity(0.05),
                            color: sigColor,
                            strokeWidth: 5,
                            strokeCap: StrokeCap.round,
                          ),
                        ),
                        Column(
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            Text(
                              score.toStringAsFixed(1),
                              style: GoogleFonts.outfit(
                                color: sigColor,
                                fontWeight: FontWeight.bold,
                                fontSize: 17,
                                letterSpacing: -0.5,
                              ),
                            ),
                            Text(
                              grade,
                              style: GoogleFonts.outfit(
                                color: Colors.white.withOpacity(0.5),
                                fontSize: 11,
                                fontWeight: FontWeight.w600,
                              ),
                            ),
                          ],
                        ),
                      ],
                    ),
                  ],
                ),

                const SizedBox(height: 24),

                // Signal badge + setup type
                Row(
                  children: [
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
                      decoration: BoxDecoration(
                        color: sigColor.withOpacity(0.12),
                        borderRadius: BorderRadius.circular(12),
                        border: Border.all(color: sigColor.withOpacity(0.25), width: 1),
                      ),
                      child: Row(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          Icon(LucideIcons.zap, color: sigColor, size: 13),
                          const SizedBox(width: 6),
                          Text(
                            signal,
                            style: GoogleFonts.outfit(
                              color: sigColor,
                              fontWeight: FontWeight.w800,
                              fontSize: 13,
                              letterSpacing: 0.5,
                            ),
                          ),
                        ],
                      ),
                    ),
                    const SizedBox(width: 10),
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                      decoration: BoxDecoration(
                        color: Colors.white.withOpacity(0.05),
                        borderRadius: BorderRadius.circular(12),
                        border: Border.all(color: Colors.white.withOpacity(0.08)),
                      ),
                      child: Text(
                        setupType,
                        style: GoogleFonts.outfit(
                          color: Colors.white.withOpacity(0.7),
                          fontSize: 12,
                          fontWeight: FontWeight.w600,
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
}

// ─── Execution Card ───────────────────────────────────────────
class _ExecutionCard extends StatelessWidget {
  final Map<String, dynamic> data;
  const _ExecutionCard({required this.data});

  @override
  Widget build(BuildContext context) {
    final Map<String, dynamic> ui = data['ui_data'] is Map ? data['ui_data'] : {};
    final double entry = _d(data['price']);
    final double stop = _d(ui['stop_loss']);
    final double t1 = _d(ui['target_1']);
    final double t2 = _d(ui['target_2']);
    final double rr = _d(ui['rr_ratio'], def: 1.5);
    final String move = ui['expected_move']?.toString() ?? '0%';

    return PremiumCard(
      borderRadius: 24,
      padding: const EdgeInsets.all(24),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              const Icon(LucideIcons.target, color: AppTheme.primaryLight, size: 16),
              const SizedBox(width: 10),
              Text(
                'TRADE SETUP',
                style: GoogleFonts.outfit(
                  color: AppTheme.textMuted,
                  fontSize: 11,
                  fontWeight: FontWeight.w600,
                  letterSpacing: 1.5,
                ),
              ),
            ],
          ),
          const SizedBox(height: 20),
          Row(
            children: [
              _tradeCell('Entry', '₹${entry.toStringAsFixed(2)}', AppTheme.primaryLight),
              _vDivider(),
              _tradeCell('Stop Loss', '₹${stop.toStringAsFixed(2)}', AppTheme.signalAvoid),
              _vDivider(),
              _tradeCell('R:R', '${rr.toStringAsFixed(1)}x', AppTheme.signalNeutral),
            ],
          ),
          const SizedBox(height: 16),
          Container(height: 1, color: Colors.white.withOpacity(0.06)),
          const SizedBox(height: 16),
          Row(
            children: [
              _tradeCell('Target 1', '₹${t1.toStringAsFixed(2)}', AppTheme.signalBuy),
              _vDivider(),
              _tradeCell('Target 2', '₹${t2.toStringAsFixed(2)}', AppTheme.signalBuy),
              _vDivider(),
              _tradeCell('Exp. Move', move, Colors.white.withOpacity(0.7)),
            ],
          ),
        ],
      ),
    );
  }

  Widget _tradeCell(String label, String value, Color color) {
    return Expanded(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.center,
        children: [
          Text(label, style: GoogleFonts.outfit(color: AppTheme.textMuted, fontSize: 10, fontWeight: FontWeight.w500, letterSpacing: 0.5)),
          const SizedBox(height: 6),
          FittedBox(
            fit: BoxFit.scaleDown,
            child: Text(
              value,
              style: GoogleFonts.outfit(color: color, fontSize: 16, fontWeight: FontWeight.bold, letterSpacing: -0.3),
            ),
          ),
        ],
      ),
    );
  }

  Widget _vDivider() => Container(width: 1, height: 36, color: Colors.white.withOpacity(0.06));
}

// ─── Regime Card ─────────────────────────────────────────────
class _RegimeCard extends StatelessWidget {
  final Map<String, dynamic> data;
  const _RegimeCard({required this.data});

  @override
  Widget build(BuildContext context) {
    final String regime = data['regime']?.toString() ?? 'UNKNOWN';
    final double mult = _d(data['regime_multiplier'], def: 1.0);
    final double rsi = _d(data['rsi']);
    final double volRatio = _d(data['volume_ratio']);
    final bool isBull = regime.contains('BULL');

    return PremiumCard(
      borderRadius: 24,
      padding: const EdgeInsets.all(24),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              const Icon(LucideIcons.globe, color: AppTheme.primaryLight, size: 16),
              const SizedBox(width: 10),
              Text('MARKET REGIME', style: GoogleFonts.outfit(color: AppTheme.textMuted, fontSize: 11, fontWeight: FontWeight.w600, letterSpacing: 1.5)),
              const Spacer(),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                decoration: BoxDecoration(
                  color: (isBull ? AppTheme.signalBuy : AppTheme.signalAvoid).withOpacity(0.12),
                  borderRadius: BorderRadius.circular(8),
                  border: Border.all(color: (isBull ? AppTheme.signalBuy : AppTheme.signalAvoid).withOpacity(0.25)),
                ),
                child: Text(
                  '${(mult * 100).toInt()}% Gate',
                  style: GoogleFonts.outfit(
                    color: isBull ? AppTheme.signalBuy : AppTheme.signalAvoid,
                    fontSize: 11,
                    fontWeight: FontWeight.w700,
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 16),
          Text(
            regime.replaceAll('_', ' '),
            style: GoogleFonts.outfit(color: Colors.white, fontSize: 20, fontWeight: FontWeight.bold, letterSpacing: -0.3),
          ),
          const SizedBox(height: 20),
          Row(
            children: [
              _statPill('RSI', rsi.toStringAsFixed(1), rsi > 60 ? AppTheme.signalBuy : rsi < 40 ? AppTheme.signalAvoid : AppTheme.signalNeutral),
              const SizedBox(width: 10),
              _statPill('Vol Ratio', '${volRatio.toStringAsFixed(1)}x', volRatio > 1.5 ? AppTheme.signalBuy : AppTheme.textMuted),
              const SizedBox(width: 10),
              _statPill('ATR', '₹${_d(data['atr']).toStringAsFixed(1)}', Colors.white.withOpacity(0.7)),
            ],
          ),
        ],
      ),
    );
  }

  Widget _statPill(String label, String val, Color color) {
    return Expanded(
      child: Container(
        padding: const EdgeInsets.symmetric(vertical: 10),
        decoration: BoxDecoration(
          color: Colors.white.withOpacity(0.04),
          borderRadius: BorderRadius.circular(12),
          border: Border.all(color: Colors.white.withOpacity(0.07)),
        ),
        child: Column(
          children: [
            Text(label, style: GoogleFonts.outfit(color: AppTheme.textMuted, fontSize: 10, fontWeight: FontWeight.w500)),
            const SizedBox(height: 4),
            Text(val, style: GoogleFonts.outfit(color: color, fontSize: 14, fontWeight: FontWeight.bold)),
          ],
        ),
      ),
    );
  }
}

// ─── Components Card ─────────────────────────────────────────
class _ComponentsCard extends StatelessWidget {
  final Map<String, dynamic> data;
  const _ComponentsCard({required this.data});

  @override
  Widget build(BuildContext context) {
    final Map<String, dynamic> components =
        data['components'] is Map ? data['components'] : {};
    if (components.isEmpty) return const SizedBox.shrink();

    return PremiumCard(
      borderRadius: 24,
      padding: const EdgeInsets.all(24),
      child: Column(
        children: components.entries.map((e) {
          final Map<String, dynamic> comp = e.value is Map ? e.value : {};
          final double score = _d(comp['score']);
          final int max = comp['max'] is int ? comp['max'] : 10;
          final double pct = (score / max).clamp(0.0, 1.0);
          final Color barColor = pct > 0.7
              ? AppTheme.signalBuy
              : pct > 0.4
                  ? AppTheme.signalNeutral
                  : AppTheme.signalAvoid;
          final String name = e.key.replaceAll('_', ' ').toUpperCase();

          return Padding(
            padding: const EdgeInsets.only(bottom: 18),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Text(name, style: GoogleFonts.outfit(color: Colors.white.withOpacity(0.8), fontSize: 12, fontWeight: FontWeight.w600)),
                    Text(
                      '${score.toStringAsFixed(1)} / $max',
                      style: GoogleFonts.outfit(color: AppTheme.textMuted, fontSize: 12),
                    ),
                  ],
                ),
                const SizedBox(height: 8),
                ClipRRect(
                  borderRadius: BorderRadius.circular(6),
                  child: LinearProgressIndicator(
                    value: pct,
                    minHeight: 6,
                    backgroundColor: Colors.white.withOpacity(0.06),
                    valueColor: AlwaysStoppedAnimation<Color>(barColor.withOpacity(0.85)),
                  ),
                ),
              ],
            ),
          );
        }).toList(),
      ),
    );
  }
}

// ─── Signal Matrix Card ───────────────────────────────────────
class _SignalMatrixCard extends StatelessWidget {
  final Map<String, dynamic> data;
  const _SignalMatrixCard({required this.data});

  @override
  Widget build(BuildContext context) {
    final bool breakout = data['breakout'] == true;
    final double rs = _d(data['relative_strength']);
    final double ema20 = _d(data['ema20']);
    final double ema50 = _d(data['ema50']);
    final double price = _d(data['price']);
    final double macd = _d(data['macd']);
    final String regime = data['regime']?.toString() ?? 'UNKNOWN';

    final signals = [
      _SignalRow('Breakout Confirmed', breakout, LucideIcons.flame),
      _SignalRow('Price > EMA20', price > ema20 && ema20 > 0, LucideIcons.trendingUp),
      _SignalRow('Price > EMA50', price > ema50 && ema50 > 0, LucideIcons.barChart2),
      _SignalRow('MACD Positive', macd > 0, LucideIcons.activity),
      _SignalRow('RS Rank > 50', rs > 50, LucideIcons.award),
      _SignalRow('Bull Market', regime.contains('BULL'), LucideIcons.sun),
    ];

    return PremiumCard(
      borderRadius: 24,
      padding: const EdgeInsets.all(24),
      child: Column(
        children: signals.asMap().entries.map((entry) {
          final s = entry.value;
          return Padding(
            padding: const EdgeInsets.only(bottom: 12),
            child: Row(
              children: [
                Container(
                  width: 32,
                  height: 32,
                  decoration: BoxDecoration(
                    color: (s.active ? AppTheme.signalBuy : Colors.white.withOpacity(0.05)).withOpacity(0.12),
                    borderRadius: BorderRadius.circular(8),
                    border: Border.all(
                      color: (s.active ? AppTheme.signalBuy : Colors.white.withOpacity(0.08)).withOpacity(s.active ? 0.3 : 1),
                    ),
                  ),
                  child: Icon(s.icon, size: 15, color: s.active ? AppTheme.signalBuy : Colors.white.withOpacity(0.2)),
                ),
                const SizedBox(width: 14),
                Expanded(
                  child: Text(
                    s.label,
                    style: GoogleFonts.outfit(
                      color: s.active ? Colors.white : Colors.white.withOpacity(0.4),
                      fontSize: 14,
                      fontWeight: s.active ? FontWeight.w600 : FontWeight.w400,
                    ),
                  ),
                ),
                Icon(
                  s.active ? LucideIcons.checkCircle : LucideIcons.xCircle,
                  color: s.active ? AppTheme.signalBuy : Colors.white.withOpacity(0.15),
                  size: 18,
                ),
              ],
            ),
          );
        }).toList(),
      ),
    );
  }
}

class _SignalRow {
  final String label;
  final bool active;
  final IconData icon;
  const _SignalRow(this.label, this.active, this.icon);
}