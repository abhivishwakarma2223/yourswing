import 'package:flutter/material.dart';
import 'package:flutter_animate/flutter_animate.dart';
import 'package:lucide_icons/lucide_icons.dart';
import 'package:google_fonts/google_fonts.dart';
import '../theme/app_theme.dart';
import 'result_screen.dart';

class SearchScreen extends StatefulWidget {
  const SearchScreen({super.key});

  @override
  State<SearchScreen> createState() => _SearchScreenState();
}

class _SearchScreenState extends State<SearchScreen> {
  final TextEditingController _controller = TextEditingController();
  final FocusNode _focusNode = FocusNode();
  bool _hasText = false;
  bool _focused = false;

  static const List<Map<String, String>> _quickPicks = [
    {'symbol': 'RELIANCE.NS', 'label': 'Reliance'},
    {'symbol': 'TCS.NS', 'label': 'TCS'},
    {'symbol': 'HDFCBANK.NS', 'label': 'HDFC Bank'},
    {'symbol': 'INFY.NS', 'label': 'Infosys'},
    {'symbol': 'ICICIBANK.NS', 'label': 'ICICI Bank'},
    {'symbol': 'ADANIPORTS.NS', 'label': 'Adani Ports'},
    {'symbol': 'TMCV.NS', 'label': 'Tata Motors'},
    {'symbol': 'WIPRO.NS', 'label': 'Wipro'},
    {'symbol': 'BAJFINANCE.NS', 'label': 'Bajaj Finance'},
    {'symbol': 'NATIONALUM.NS', 'label': 'Nat. Aluminium'},
  ];

  @override
  void initState() {
    super.initState();
    _controller.addListener(() => setState(() => _hasText = _controller.text.isNotEmpty));
    _focusNode.addListener(() => setState(() => _focused = _focusNode.hasFocus));
    WidgetsBinding.instance.addPostFrameCallback((_) => _focusNode.requestFocus());
  }

  @override
  void dispose() {
    _controller.dispose();
    _focusNode.dispose();
    super.dispose();
  }

  void _search(String raw) {
    String symbol = raw.trim().toUpperCase();
    if (symbol.isEmpty) return;
    if (!symbol.contains('.')) symbol = '$symbol.NS';
    Navigator.push(context, MaterialPageRoute(builder: (_) => ResultScreen(symbol: symbol)));
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
        // resizeToAvoidBottomInset keeps layout safe when keyboard opens
        resizeToAvoidBottomInset: true,
        body: SafeArea(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // ── Top bar ──────────────────────────────────────
              Padding(
                padding: const EdgeInsets.fromLTRB(20, 16, 20, 0),
                child: Row(
                  children: [
                    // Back
                    GestureDetector(
                      onTap: () => Navigator.pop(context),
                      child: Container(
                        width: 44,
                        height: 44,
                        decoration: BoxDecoration(
                          color: Colors.white.withOpacity(0.05),
                          borderRadius: BorderRadius.circular(13),
                          border: Border.all(color: Colors.white.withOpacity(0.08)),
                        ),
                        child: const Icon(LucideIcons.chevronLeft, color: Colors.white, size: 20),
                      ),
                    ),
                    const SizedBox(width: 12),

                    // Search bar — takes remaining space
                    Expanded(
                      child: _SearchBar(
                        controller: _controller,
                        focusNode: _focusNode,
                        focused: _focused,
                        hasText: _hasText,
                        onSubmit: _search,
                        onClear: () => _controller.clear(),
                      ),
                    ),

                    const SizedBox(width: 10),

                    // Go button
                    GestureDetector(
                      onTap: () => _search(_controller.text),
                      child: Container(
                        width: 50,
                        height: 50,
                        decoration: BoxDecoration(
                          gradient: const LinearGradient(
                            colors: [AppTheme.primaryLight, AppTheme.primaryDark],
                            begin: Alignment.topLeft,
                            end: Alignment.bottomRight,
                          ),
                          borderRadius: BorderRadius.circular(14),
                          boxShadow: [
                            BoxShadow(
                              color: AppTheme.primaryLight.withOpacity(0.28),
                              blurRadius: 14,
                              offset: const Offset(0, 5),
                            ),
                          ],
                        ),
                        child: const Icon(LucideIcons.arrowRight, color: Colors.black, size: 20),
                      ),
                    ),
                  ],
                ).animate().fade().slideY(begin: -0.15),
              ),

              const SizedBox(height: 28),

              // ── Scrollable content ────────────────────────────
              Expanded(
                child: SingleChildScrollView(
                  padding: const EdgeInsets.fromLTRB(20, 0, 20, 40),
                  keyboardDismissBehavior: ScrollViewKeyboardDismissBehavior.onDrag,
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      // Hint pill
                      Container(
                        width: double.infinity,
                        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 11),
                        decoration: BoxDecoration(
                          color: AppTheme.primaryLight.withOpacity(0.05),
                          borderRadius: BorderRadius.circular(12),
                          border: Border.all(color: AppTheme.primaryLight.withOpacity(0.12)),
                        ),
                        child: Row(
                          children: [
                            Icon(LucideIcons.info, color: AppTheme.primaryLight.withOpacity(0.6), size: 14),
                            const SizedBox(width: 10),
                            Expanded(
                              child: Text(
                                'Type RELIANCE or TCS — .NS is added automatically',
                                style: GoogleFonts.outfit(
                                  color: Colors.white.withOpacity(0.45),
                                  fontSize: 12,
                                ),
                              ),
                            ),
                          ],
                        ),
                      ).animate().fade(delay: 60.ms),

                      const SizedBox(height: 28),

                      Text(
                        'Quick Picks',
                        style: GoogleFonts.outfit(
                          color: Colors.white,
                          fontSize: 17,
                          fontWeight: FontWeight.bold,
                        ),
                      ).animate().fade(delay: 100.ms),
                      const SizedBox(height: 14),

                      // Wrap chips — no overflow risk
                      Wrap(
                        spacing: 8,
                        runSpacing: 8,
                        children: _quickPicks.asMap().entries.map((e) {
                          final i = e.key;
                          final pick = e.value;
                          return _Chip(
                            ticker: pick['symbol']!.replaceAll('.NS', ''),
                            label: pick['label']!,
                            delay: Duration(milliseconds: 110 + i * 30),
                            onTap: () => _search(pick['symbol']!),
                          );
                        }).toList(),
                      ),


                    ],
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

// ─── Custom Search Bar (no default TextField border rectangle) ─
class _SearchBar extends StatelessWidget {
  final TextEditingController controller;
  final FocusNode focusNode;
  final bool focused;
  final bool hasText;
  final ValueChanged<String> onSubmit;
  final VoidCallback onClear;

  const _SearchBar({
    required this.controller,
    required this.focusNode,
    required this.focused,
    required this.hasText,
    required this.onSubmit,
    required this.onClear,
  });

  @override
  Widget build(BuildContext context) {
    return AnimatedContainer(
      duration: const Duration(milliseconds: 200),
      height: 50,
      decoration: BoxDecoration(
        color: AppTheme.surfaceWhite.withOpacity(0.55),
        borderRadius: BorderRadius.circular(14),
        border: Border.all(
          color: focused
              ? AppTheme.primaryLight.withOpacity(0.45)
              : Colors.white.withOpacity(0.08),
          width: 1.5,
        ),
        boxShadow: focused
            ? [BoxShadow(color: AppTheme.primaryLight.withOpacity(0.07), blurRadius: 18, spreadRadius: -4)]
            : [],
      ),
      child: Row(
        children: [
          const SizedBox(width: 14),
          Icon(
            LucideIcons.search,
            color: focused ? AppTheme.primaryLight : Colors.white.withOpacity(0.3),
            size: 17,
          ),
          const SizedBox(width: 10),
          Expanded(
            child: TextField(
              controller: controller,
              focusNode: focusNode,
              textInputAction: TextInputAction.search,
              textCapitalization: TextCapitalization.characters,
              onSubmitted: onSubmit,
              style: GoogleFonts.outfit(
                color: Colors.white,
                fontSize: 15,
                fontWeight: FontWeight.w600,
                letterSpacing: 0.4,
              ),
              // Remove all borders — the Container handles visual styling
              decoration: InputDecoration(
                hintText: 'e.g. RELIANCE, TCS…',
                hintStyle: GoogleFonts.outfit(
                  color: Colors.white.withOpacity(0.22),
                  fontSize: 14,
                  fontWeight: FontWeight.w400,
                ),
                isDense: true,
                contentPadding: EdgeInsets.zero,
                border: InputBorder.none,
                enabledBorder: InputBorder.none,
                focusedBorder: InputBorder.none,
                errorBorder: InputBorder.none,
                disabledBorder: InputBorder.none,
              ),
            ),
          ),
          if (hasText)
            GestureDetector(
              onTap: onClear,
              child: Padding(
                padding: const EdgeInsets.symmetric(horizontal: 10),
                child: Icon(LucideIcons.x, color: Colors.white.withOpacity(0.3), size: 16),
              ),
            )
          else
            const SizedBox(width: 12),
        ],
      ),
    );
  }
}

// ─── Quick pick chip ─────────────────────────────────────────
class _Chip extends StatelessWidget {
  final String ticker;
  final String label;
  final Duration delay;
  final VoidCallback onTap;

  const _Chip({required this.ticker, required this.label, required this.delay, required this.onTap});

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 9),
        decoration: BoxDecoration(
          color: AppTheme.surfaceWhite.withOpacity(0.45),
          borderRadius: BorderRadius.circular(11),
          border: Border.all(color: Colors.white.withOpacity(0.08)),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          mainAxisSize: MainAxisSize.min,
          children: [
            Text(ticker, style: GoogleFonts.outfit(color: Colors.white, fontSize: 13, fontWeight: FontWeight.bold)),
            Text(label,  style: GoogleFonts.outfit(color: AppTheme.textMuted, fontSize: 10)),
          ],
        ),
      ),
    ).animate().fade(delay: delay).scale(begin: const Offset(0.88, 0.88), curve: Curves.easeOutBack);
  }
}

