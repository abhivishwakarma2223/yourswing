import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

class AppTheme {
  // Primary Brand Colors
  static const Color primaryLight = Color(0xFF00E676); // Vibrant Neon Green
  static const Color primaryDark = Color(0xFF00B248);
  
  // Background & Surface (Dark Theme)
  static const Color background = Color(0xFF0F172A); // Deep slate
  static const Color backgroundDarker = Color(0xFF020617); // Almost black
  static const Color surfaceWhite = Color(0xFF1E293B); // Dark surface
  static const Color cardColor = Color(0xFF1E293B);
  
  // Text Colors
  static const Color textDark = Colors.white; // White text for dark mode
  static const Color textMuted = Color(0xFF94A3B8); // Slate 400
  
  // Signal Colors
  static const Color signalBuy = Color(0xFF22C55E);
  static const Color signalAvoid = Color(0xFFEF4444);
  static const Color signalNeutral = Color(0xFFEAB308);

  static ThemeData get lightTheme {
    return ThemeData(
      useMaterial3: true,
      brightness: Brightness.dark,
      colorScheme: ColorScheme.dark(
        primary: primaryLight,
        background: background,
        surface: surfaceWhite,
      ),
      scaffoldBackgroundColor: Colors.transparent, // For gradient backgrounds
      
      // Typography
      textTheme: GoogleFonts.outfitTextTheme().copyWith(
        displayLarge: GoogleFonts.outfit(
          color: textDark,
          fontWeight: FontWeight.w700,
          letterSpacing: -1.0,
        ),
        displayMedium: GoogleFonts.outfit(
          color: textDark,
          fontWeight: FontWeight.w700,
          letterSpacing: -0.5,
        ),
        titleLarge: GoogleFonts.outfit(
          color: textDark,
          fontWeight: FontWeight.w600,
        ),
        bodyLarge: GoogleFonts.outfit(
          color: textDark,
          fontWeight: FontWeight.w400,
        ),
        bodyMedium: GoogleFonts.outfit(
          color: textMuted,
          fontWeight: FontWeight.w400,
        ),
      ),
      
      // Inputs
      inputDecorationTheme: InputDecorationTheme(
        filled: true,
        fillColor: surfaceWhite,
        contentPadding: const EdgeInsets.symmetric(horizontal: 24, vertical: 16),
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(16),
          borderSide: BorderSide.none,
        ),
        enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(16),
          borderSide: BorderSide(color: Colors.white.withOpacity(0.05)),
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(16),
          borderSide: const BorderSide(color: primaryLight, width: 2),
        ),
        hintStyle: GoogleFonts.outfit(color: textMuted),
      ),
    );
  }
}
