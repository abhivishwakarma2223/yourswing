import 'package:flutter/material.dart';
import 'package:lucide_icons/lucide_icons.dart';
import 'dashboard_screen.dart';
import 'portfolio_screen.dart';
import '../theme/app_theme.dart';

class MainNavigationScreen extends StatefulWidget {
  const MainNavigationScreen({super.key});

  @override
  State<MainNavigationScreen> createState() => _MainNavigationScreenState();
}

class _MainNavigationScreenState extends State<MainNavigationScreen> {
  int _selectedIndex = 0;

  final List<Widget> _screens = [
    const DashboardScreen(),
    const PortfolioScreen(),
  ];

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: IndexedStack(
        index: _selectedIndex,
        children: _screens,
      ),
      bottomNavigationBar: Container(
        padding: const EdgeInsets.only(top: 8),
        decoration: const BoxDecoration(
          color: Color(0xFF080C14), // Pure dark to match dashboard footer
        ),
        child: BottomNavigationBar(
          currentIndex: _selectedIndex,
          onTap: (index) => setState(() => _selectedIndex = index),
          backgroundColor: Colors.transparent,
          elevation: 0,
          selectedItemColor: const Color(0xFF4F8EF7),
          unselectedItemColor: Colors.white.withOpacity(0.2),
          showSelectedLabels: false, // Removed labels as requested
          showUnselectedLabels: false, // Removed labels as requested
          type: BottomNavigationBarType.fixed,
          iconSize: 28, // Slightly larger icons for professional look
          items: const [
            BottomNavigationBarItem(
              icon: Icon(LucideIcons.home), // Using Home icon as requested
              label: '',
            ),
            BottomNavigationBarItem(
              icon: Icon(LucideIcons.briefcase), // Using Briefcase/Portfolio icon
              label: '',
            ),
          ],
        ),
      ),
    );
  }
}
