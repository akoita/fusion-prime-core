#!/bin/bash
# Test Report Viewer
# Opens test reports in the default browser

set -e

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
REPORTS_DIR="$PROJECT_ROOT/test-reports"
LATEST_DIR="$REPORTS_DIR/latest"

echo "========================================="
echo "Fusion Prime Test Report Viewer"
echo "========================================="

# Check if reports exist
if [ ! -d "$REPORTS_DIR" ]; then
    echo "No test reports found. Run tests first:"
    echo "  ./scripts/generate-test-reports.sh"
    exit 1
fi

# Show available reports
echo "Available test reports:"
echo ""

if [ -d "$LATEST_DIR" ]; then
    echo -e "${GREEN}Latest Report:${NC}"
    echo "  HTML: $LATEST_DIR/test-report.html"
    echo "  JSON: $LATEST_DIR/test-results.json"
    echo ""
fi

echo "All Reports:"
ls -la "$REPORTS_DIR" | grep "^d" | awk '{print "  " $9 " (" $6 " " $7 " " $8 ")"}' | grep -v "^  \.$" | grep -v "^  \.\.$"

echo ""

# Ask user which report to view
if [ -d "$LATEST_DIR" ]; then
    read -p "View latest report? (y/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        REPORT_DIR="$LATEST_DIR"
    else
        echo "Enter report timestamp (e.g., 20241219-143022):"
        read -r TIMESTAMP
        REPORT_DIR="$REPORTS_DIR/$TIMESTAMP"

        if [ ! -d "$REPORT_DIR" ]; then
            echo "Report not found: $REPORT_DIR"
            exit 1
        fi
    fi
else
    echo "Enter report timestamp (e.g., 20241219-143022):"
    read -r TIMESTAMP
    REPORT_DIR="$REPORTS_DIR/$TIMESTAMP"

    if [ ! -d "$REPORT_DIR" ]; then
        echo "Report not found: $REPORT_DIR"
        exit 1
    fi
fi

# Show report contents
echo ""
echo "Report Contents:"
echo "  Directory: $REPORT_DIR"
echo ""

if [ -f "$REPORT_DIR/test-report.html" ]; then
    echo -e "${GREEN}✓${NC} HTML Report: test-report.html"
fi

if [ -f "$REPORT_DIR/test-results.json" ]; then
    echo -e "${GREEN}✓${NC} JSON Report: test-results.json"
fi

# Show individual test suite results
for status_file in "$REPORT_DIR"/*.status; do
    if [ -f "$status_file" ]; then
        local suite_name=$(basename "$status_file" .status)
        local status=$(cat "$status_file")
        local status_icon="✓"
        local status_color="${GREEN}"

        if [ "$status" = "FAIL" ]; then
            status_icon="✗"
            status_color="${RED}"
        fi

        echo -e "  ${status_color}${status_icon}${NC} $suite_name: $status"
    fi
done

echo ""

# Open HTML report
if [ -f "$REPORT_DIR/test-report.html" ]; then
    read -p "Open HTML report in browser? (y/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        if command -v open >/dev/null 2>&1; then
            open "$REPORT_DIR/test-report.html"
        elif command -v xdg-open >/dev/null 2>&1; then
            xdg-open "$REPORT_DIR/test-report.html"
        elif command -v start >/dev/null 2>&1; then
            start "$REPORT_DIR/test-report.html"
        else
            echo "Please open manually: $REPORT_DIR/test-report.html"
        fi
    fi
fi

# Show JSON summary
if [ -f "$REPORT_DIR/test-results.json" ]; then
    read -p "Show JSON summary? (y/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo ""
        echo "JSON Summary:"
        cat "$REPORT_DIR/test-results.json" | jq . 2>/dev/null || cat "$REPORT_DIR/test-results.json"
    fi
fi

echo ""
echo -e "${BLUE}Report viewing complete!${NC}"
