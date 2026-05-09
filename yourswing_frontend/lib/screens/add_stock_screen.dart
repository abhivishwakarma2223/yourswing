import 'package:flutter/material.dart';
import 'package:lucide_icons/lucide_icons.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:flutter_animate/flutter_animate.dart';
import '../theme/app_theme.dart';
import '../services/portfolio_service.dart';
import '../models/portfolio_item.dart';

class AddStockScreen extends StatefulWidget {
  const AddStockScreen({super.key});

  @override
  State<AddStockScreen> createState() => _AddStockScreenState();
}

class _AddStockScreenState extends State<AddStockScreen> {
  final _portfolioService = PortfolioService();
  final _symbolController = TextEditingController();
  final _qtyController = TextEditingController();
  final _priceController = TextEditingController();
  bool _isSaving = false;

  Future<void> _handleSave() async {
    if (_symbolController.text.isEmpty || _qtyController.text.isEmpty || _priceController.text.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Please fill all fields')),
      );
      return;
    }

    setState(() => _isSaving = true);

    String symbol = _symbolController.text.trim().toUpperCase();
    if (!symbol.contains('.')) symbol = '$symbol.NS';

    final newItem = PortfolioItem(
      symbol: symbol,
      name: symbol,
      quantity: double.tryParse(_qtyController.text) ?? 0,
      averagePrice: double.tryParse(_priceController.text) ?? 0,
    );

    await _portfolioService.saveStock(newItem);
    
    if (mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('$symbol added to portfolio'),
          backgroundColor: AppTheme.signalBuy,
        ),
      );
      
      // Clear fields
      _symbolController.clear();
      _qtyController.clear();
      _priceController.clear();
      setState(() => _isSaving = false);
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
          title: Text(
            'Add Stock',
            style: GoogleFonts.outfit(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 24),
          ),
        ),
        body: SingleChildScrollView(
          padding: const EdgeInsets.all(24),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                'Grow your portfolio by tracking new holdings.',
                style: GoogleFonts.outfit(color: Colors.white38, fontSize: 16),
              ).animate().fade().slideX(begin: -0.1),
              
              const SizedBox(height: 40),
              
              _buildInputField(
                controller: _symbolController,
                label: 'SYMBOL',
                hint: 'e.g. RELIANCE, TCS',
                icon: LucideIcons.search,
              ).animate().fade(delay: 100.ms).slideY(begin: 0.1),
              
              const SizedBox(height: 24),
              
              _buildInputField(
                controller: _qtyController,
                label: 'QUANTITY',
                hint: '0.00',
                icon: LucideIcons.layers,
                isNumeric: true,
              ).animate().fade(delay: 200.ms).slideY(begin: 0.1),
              
              const SizedBox(height: 24),
              
              _buildInputField(
                controller: _priceController,
                label: 'AVERAGE PRICE',
                hint: '₹ 0.00',
                icon: LucideIcons.indianRupee,
                isNumeric: true,
              ).animate().fade(delay: 300.ms).slideY(begin: 0.1),
              
              const SizedBox(height: 48),
              
              SizedBox(
                width: double.infinity,
                height: 64,
                child: ElevatedButton(
                  style: ElevatedButton.styleFrom(
                    backgroundColor: AppTheme.primaryLight,
                    foregroundColor: Colors.black,
                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
                    elevation: 0,
                  ),
                  onPressed: _isSaving ? null : _handleSave,
                  child: _isSaving
                      ? const CircularProgressIndicator(color: Colors.black)
                      : Text(
                          'ADD TO PORTFOLIO',
                          style: GoogleFonts.outfit(
                            fontWeight: FontWeight.w800,
                            fontSize: 16,
                            letterSpacing: 1.5,
                          ),
                        ),
                ),
              ).animate().fade(delay: 400.ms).scale(),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildInputField({
    required TextEditingController controller,
    required String label,
    required String hint,
    required IconData icon,
    bool isNumeric = false,
  }) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          label,
          style: GoogleFonts.outfit(
            color: AppTheme.primaryLight.withOpacity(0.6),
            fontSize: 12,
            fontWeight: FontWeight.bold,
            letterSpacing: 1.5,
          ),
        ),
        const SizedBox(height: 12),
        TextField(
          controller: controller,
          keyboardType: isNumeric ? TextInputType.number : TextInputType.text,
          style: const TextStyle(color: Colors.white, fontSize: 18),
          decoration: InputDecoration(
            hintText: hint,
            hintStyle: TextStyle(color: Colors.white.withOpacity(0.1)),
            prefixIcon: Icon(icon, color: Colors.white24, size: 20),
            filled: true,
            fillColor: Colors.white.withOpacity(0.03),
            contentPadding: const EdgeInsets.symmetric(horizontal: 20, vertical: 20),
            enabledBorder: OutlineInputBorder(
              borderRadius: BorderRadius.circular(20),
              borderSide: BorderSide(color: Colors.white.withOpacity(0.05)),
            ),
            focusedBorder: OutlineInputBorder(
              borderRadius: BorderRadius.circular(20),
              borderSide: const BorderSide(color: AppTheme.primaryLight, width: 1.5),
            ),
          ),
        ),
      ],
    );
  }
}
