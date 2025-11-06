"""
AgroPulse Codebase Cleanup and Optimization
============================================

This script removes redundant files and consolidates detection logic
after integrating Kindwise API for hybrid disease detection.

Redundancies Identified:
1. Standalone disease detectors superseded by crop-specific suites
2. Duplicate symptom detection code across modules
3. Overlapping integration logic

Benefits of Cleanup:
- Reduced code maintenance burden
- Clearer architecture
- Faster onboarding for new developers
- Smaller deployment footprint

Author: AgroPulse Team
Date: November 2025
"""

import os
import shutil
from pathlib import Path
from typing import List, Dict
from datetime import datetime


class CodebaseCleanup:
    """Manages removal of redundant files and code consolidation"""
    
    # Files identified as redundant
    REDUNDANT_FILES = [
        "nvr_system/disease_detection/powdery_mildew_detector.py",
        "nvr_system/disease_detection/downy_mildew_detector.py",
        "nvr_system/disease_detection/botrytis_detector.py",
    ]
    
    # Reasons for removal
    REMOVAL_REASONS = {
        "powdery_mildew_detector.py": (
            "Superseded by integrated powdery mildew detection in crop-specific suites "
            "(tomato, cucumber, pepper, strawberry, grape, etc.). Each crop suite now "
            "handles powdery mildew with crop-specific parameters."
        ),
        "downy_mildew_detector.py": (
            "Replaced by crop-specific downy mildew detection in tomato, cucumber, "
            "lettuce, grape, and onion disease suites. Integrated approach provides "
            "better crop-specific symptom analysis."
        ),
        "botrytis_detector.py": (
            "Integrated into strawberry, grape, tomato, and pepper disease suites. "
            "Gray mold detection now uses crop-specific lesion patterns and "
            "environmental correlation."
        ),
    }
    
    def __init__(self, workspace_root: str):
        """
        Args:
            workspace_root: Root directory of AgroPulse workspace
        """
        self.root = Path(workspace_root)
        self.backup_dir = self.root / "cleanup_backups" / datetime.now().strftime("%Y%m%d_%H%M%S")
        self.cleanup_log = []
    
    def analyze_redundancy(self) -> Dict[str, Dict]:
        """
        Analyze files for redundancy without deletion
        Returns detailed report
        """
        report = {}
        
        for file_path in self.REDUNDANT_FILES:
            full_path = self.root / file_path
            filename = os.path.basename(file_path)
            
            if full_path.exists():
                file_size = full_path.stat().st_size
                line_count = self._count_lines(full_path)
                
                report[filename] = {
                    "path": str(full_path),
                    "size_kb": file_size / 1024,
                    "lines": line_count,
                    "reason": self.REMOVAL_REASONS.get(filename, "No reason specified"),
                    "status": "exists",
                    "recommendation": "REMOVE"
                }
            else:
                report[filename] = {
                    "status": "not_found",
                    "recommendation": "N/A"
                }
        
        return report
    
    def create_backup(self) -> bool:
        """
        Create backup of files before deletion
        Returns True if successful
        """
        try:
            self.backup_dir.mkdir(parents=True, exist_ok=True)
            
            for file_path in self.REDUNDANT_FILES:
                full_path = self.root / file_path
                if full_path.exists():
                    # Create backup with same structure
                    backup_path = self.backup_dir / os.path.basename(file_path)
                    shutil.copy2(full_path, backup_path)
                    self.cleanup_log.append(f"✓ Backed up: {file_path}")
            
            # Create backup manifest
            manifest_path = self.backup_dir / "MANIFEST.txt"
            with open(manifest_path, 'w') as f:
                f.write("AgroPulse Cleanup Backup\n")
                f.write(f"Created: {datetime.now().isoformat()}\n")
                f.write("=" * 60 + "\n\n")
                
                for filename, reason in self.REMOVAL_REASONS.items():
                    f.write(f"File: {filename}\n")
                    f.write(f"Reason: {reason}\n")
                    f.write("-" * 60 + "\n")
            
            self.cleanup_log.append(f"✓ Backup created: {self.backup_dir}")
            return True
            
        except Exception as e:
            self.cleanup_log.append(f"❌ Backup failed: {e}")
            return False
    
    def remove_redundant_files(self, create_backup_first: bool = True) -> Dict[str, str]:
        """
        Remove redundant files
        
        Args:
            create_backup_first: Create backup before deletion (recommended)
        
        Returns:
            Dict of filename -> status
        """
        if create_backup_first:
            if not self.create_backup():
                return {"error": "Backup failed, aborting cleanup"}
        
        results = {}
        
        for file_path in self.REDUNDANT_FILES:
            full_path = self.root / file_path
            filename = os.path.basename(file_path)
            
            try:
                if full_path.exists():
                    full_path.unlink()
                    results[filename] = "REMOVED"
                    self.cleanup_log.append(f"✓ Removed: {file_path}")
                else:
                    results[filename] = "NOT_FOUND"
                    self.cleanup_log.append(f"⚠️  Not found: {file_path}")
                    
            except Exception as e:
                results[filename] = f"ERROR: {e}"
                self.cleanup_log.append(f"❌ Failed to remove {file_path}: {e}")
        
        return results
    
    def calculate_space_savings(self) -> Dict[str, float]:
        """Calculate disk space to be saved"""
        total_bytes = 0
        total_lines = 0
        
        for file_path in self.REDUNDANT_FILES:
            full_path = self.root / file_path
            if full_path.exists():
                total_bytes += full_path.stat().st_size
                total_lines += self._count_lines(full_path)
        
        return {
            "bytes": total_bytes,
            "kilobytes": total_bytes / 1024,
            "megabytes": total_bytes / (1024 * 1024),
            "lines_of_code": total_lines
        }
    
    def _count_lines(self, file_path: Path) -> int:
        """Count lines in a file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return sum(1 for _ in f)
        except Exception:
            return 0
    
    def generate_cleanup_report(self) -> str:
        """Generate comprehensive cleanup report"""
        report = []
        report.append("=" * 70)
        report.append("AGROPULSE CODEBASE CLEANUP REPORT")
        report.append("=" * 70)
        report.append(f"Generated: {datetime.now().isoformat()}")
        report.append("")
        
        # Redundancy analysis
        report.append("📊 REDUNDANCY ANALYSIS")
        report.append("-" * 70)
        redundancy_report = self.analyze_redundancy()
        
        for filename, details in redundancy_report.items():
            if details.get('status') == 'exists':
                report.append(f"\n{filename}")
                report.append(f"  Size: {details['size_kb']:.1f} KB")
                report.append(f"  Lines: {details['lines']:,}")
                report.append(f"  Reason: {details['reason']}")
                report.append(f"  Action: {details['recommendation']}")
        
        # Space savings
        report.append("\n" + "=" * 70)
        report.append("💾 SPACE SAVINGS ESTIMATE")
        report.append("-" * 70)
        savings = self.calculate_space_savings()
        report.append(f"Total file size: {savings['kilobytes']:.1f} KB")
        report.append(f"Total lines: {savings['lines_of_code']:,} LOC")
        report.append("")
        
        # Architecture benefits
        report.append("=" * 70)
        report.append("🏗️  ARCHITECTURE IMPROVEMENTS")
        report.append("-" * 70)
        report.append("✓ Unified detection via unified_disease_detector.py")
        report.append("✓ Kindwise API integration for 288+ diseases")
        report.append("✓ Hybrid approach (rule-based + AI)")
        report.append("✓ Crop-specific disease suites (18 modules)")
        report.append("✓ Farmer-friendly API with EPPO codes")
        report.append("✓ Offline capability with fallback")
        report.append("✓ Response caching to reduce API costs")
        report.append("")
        
        # New architecture
        report.append("=" * 70)
        report.append("🔄 NEW DETECTION FLOW")
        report.append("-" * 70)
        report.append("1. Image Upload → farmer_api.py")
        report.append("2. Quality Validation → ImageQualityValidator")
        report.append("3. Detection Routing → UnifiedDiseaseDetector")
        report.append("   ├─ Rule-based (local, fast, 145+ diseases)")
        report.append("   └─ Kindwise AI (cloud, 288+ diseases, EPPO codes)")
        report.append("4. Result Fusion → Confidence boosting if agreement")
        report.append("5. Farmer Output → Treatment recommendations + EPPO codes")
        report.append("")
        
        # Cleanup log
        if self.cleanup_log:
            report.append("=" * 70)
            report.append("📝 CLEANUP LOG")
            report.append("-" * 70)
            report.extend(self.cleanup_log)
            report.append("")
        
        report.append("=" * 70)
        report.append("✓ Cleanup analysis complete")
        report.append("=" * 70)
        
        return "\n".join(report)


def main():
    """Run cleanup analysis and optionally execute cleanup"""
    import sys
    
    # Get workspace root
    workspace_root = r"C:\Users\Codeternal\Desktop\AgroPulse"
    
    print("AgroPulse Codebase Cleanup Tool")
    print("=" * 70)
    print()
    
    # Initialize cleanup manager
    cleanup = CodebaseCleanup(workspace_root)
    
    # Generate report
    print("Analyzing redundant files...")
    report = cleanup.generate_cleanup_report()
    print(report)
    
    # Save report to file
    report_path = Path(workspace_root) / "CLEANUP_REPORT.md"
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(report)
    
    print(f"\n✓ Report saved to: {report_path}")
    
    # Ask for confirmation before cleanup
    print("\n" + "=" * 70)
    print("⚠️  WARNING: This will delete redundant files")
    print("=" * 70)
    
    # For automation, use environment variable
    if os.getenv("AGROPULSE_AUTO_CLEANUP") == "yes":
        response = "yes"
    else:
        response = input("\nProceed with cleanup? (yes/no): ").strip().lower()
    
    if response == "yes":
        print("\n🗑️  Proceeding with cleanup...")
        results = cleanup.remove_redundant_files(create_backup_first=True)
        
        print("\nCleanup Results:")
        for filename, status in results.items():
            print(f"  {filename}: {status}")
        
        print(f"\n✓ Backup location: {cleanup.backup_dir}")
        print("✓ Cleanup completed successfully")
    else:
        print("\n⚠️  Cleanup cancelled. No files were modified.")
    
    print("\n" + "=" * 70)


if __name__ == "__main__":
    main()
