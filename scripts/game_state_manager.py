#!/usr/bin/env python3
"""
GameState Manager - Manage game state persistence using Markdown files

This module provides functionality to save and load StockTradingGame state
to/from Markdown files for persistence and debugging purposes.
"""

import os
import json
import re
from datetime import datetime
from typing import Dict, Any, Optional, List
from pathlib import Path


class GameStateManager:
    """
    Manager for saving and loading game state to/from Markdown files
    
    Features:
    - Save game state to Markdown format
    - Load game state from Markdown files
    - Auto-save on state changes
    - Debug-friendly formatting
    - Version control support
    """
    
    def __init__(self, save_dir: str = "./game_states"):
        """
        Initialize GameStateManager
        
        Args:
            save_dir: Directory to save game state files
        """
        self.save_dir = Path(save_dir)
        self.save_dir.mkdir(exist_ok=True)
        
        # Version info
        self.version = "1.0.0"
        self.created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
    def save_game_state(self, game_state: Dict[str, Any], game_id: str, 
                       auto_save: bool = True) -> str:
        """
        Save game state to Markdown file
        
        Args:
            game_state: The game state dictionary
            game_id: Unique identifier for the game
            auto_save: Whether this is an auto-save
            
        Returns:
            Path to the saved Markdown file
        """
        # Generate filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"game_state_{game_id}_{timestamp}.md"
        filepath = self.save_dir / filename
        
        # Create Markdown content
        markdown_content = self._generate_markdown_content(
            game_state, game_id, auto_save
        )
        
        # Write to file
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(markdown_content)
        
        # Create latest symlink
        latest_file = self.save_dir / f"game_state_{game_id}_latest.md"
        if latest_file.exists():
            latest_file.unlink()
        latest_file.symlink_to(filename)
        
        return str(filepath)
    
    def load_game_state(self, game_id: str, use_latest: bool = True) -> Optional[Dict[str, Any]]:
        """
        Load game state from Markdown file
        
        Args:
            game_id: Unique identifier for the game
            use_latest: Whether to use the latest file
            
        Returns:
            Game state dictionary or None if not found
        """
        if use_latest:
            filepath = self.save_dir / f"game_state_{game_id}_latest.md"
            if not filepath.exists():
                return None
        else:
            # Find all files for this game
            pattern = f"game_state_{game_id}_*.md"
            files = list(self.save_dir.glob(pattern))
            if not files:
                return None
            # Use the most recent file
            filepath = max(files, key=lambda x: x.stat().st_mtime)
        
        # Parse Markdown file
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        return self._parse_markdown_content(content)
    
    def list_game_states(self, game_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        List all saved game states
        
        Args:
            game_id: Filter by game ID, None for all games
            
        Returns:
            List of game state info dictionaries
        """
        game_states = []
        
        if game_id:
            pattern = f"game_state_{game_id}_*.md"
            files = list(self.save_dir.glob(pattern))
        else:
            pattern = "game_state_*.md"
            files = list(self.save_dir.glob(pattern))
        
        for filepath in files:
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Extract basic info from filename
                filename = filepath.name
                match = re.match(r"game_state_(.+?)_(\d{8}_\d{6})\.md", filename)
                if match:
                    game_id_from_file = match.group(1)
                    timestamp = match.group(2)
                    
                    # Extract basic info from content
                    basic_info = self._extract_basic_info(content)
                    
                    game_states.append({
                        'file_path': str(filepath),
                        'game_id': game_id_from_file,
                        'timestamp': timestamp,
                        'basic_info': basic_info,
                        'size': filepath.stat().st_size,
                        'modified': datetime.fromtimestamp(filepath.stat().st_mtime)
                    })
            except Exception as e:
                print(f"Error reading file {filepath}: {e}")
        
        # Sort by timestamp (newest first)
        game_states.sort(key=lambda x: x['timestamp'], reverse=True)
        
        return game_states
    
    def delete_game_state(self, game_id: str, timestamp: Optional[str] = None) -> bool:
        """
        Delete game state file(s)
        
        Args:
            game_id: Game ID to delete
            timestamp: Specific timestamp to delete, None for all
            
        Returns:
            True if deletion was successful
        """
        if timestamp:
            filename = f"game_state_{game_id}_{timestamp}.md"
            filepath = self.save_dir / filename
            if filepath.exists():
                filepath.unlink()
                return True
        else:
            # Delete all files for this game
            pattern = f"game_state_{game_id}_*.md"
            files = list(self.save_dir.glob(pattern))
            for filepath in files:
                filepath.unlink()
            return len(files) > 0
        
        return False
    
    def _generate_markdown_content(self, game_state: Dict[str, Any], 
                                 game_id: str, auto_save: bool) -> str:
        """
        Generate Markdown content from game state
        
        Args:
            game_state: The game state dictionary
            game_id: Game ID
            auto_save: Whether this is an auto-save
            
        Returns:
            Markdown formatted string
        """
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Extract portfolio info
        portfolio_info = game_state.get('portfolio', {})
        cash_balance = game_state.get('cash_balance', 0)
        current_date = game_state.get('current_date', 'N/A')
        current_stock = game_state.get('current_stock', 'N/A')
        
        # Calculate portfolio summary
        total_portfolio_value = sum(
            pos.get('quantity', 0) * game_state.get('current_prices', {}).get(pos.get('symbol', {}), {}).get('close', 0)
            for pos in portfolio_info.values()
        )
        
        # Generate Markdown
        markdown = f"""# Stock Trading Game State

## 📋 Game Information

- **Game ID**: {game_id}
- **Version**: {self.version}
- **Created**: {self.created_at}
- **Last Updated**: {timestamp}
- **Auto Save**: {'Yes' if auto_save else 'No'}
- **Current Stock**: {current_stock}
- **Current Date**: {current_date}

## 💰 Portfolio Summary

- **Cash Balance**: ${cash_balance:,.2f}
- **Portfolio Value**: ${total_portfolio_value:,.2f}
- **Total Assets**: ${cash_balance + total_portfolio_value:,.2f}

## 📊 Current Holdings

"""
        
        if not portfolio_info:
            markdown += "*No holdings*\n\n"
        else:
            markdown += "| Symbol | Quantity | Avg Price | Current Price | Market Value | P&L |\n"
            markdown += "|--------|----------|-----------|---------------|---------------|-----|\n"
            
            for symbol, position in portfolio_info.items():
                quantity = position.get('quantity', 0)
                avg_price = position.get('avg_price', 0)
                current_price = game_state.get('current_prices', {}).get(symbol, {}).get('close', 0)
                market_value = quantity * current_price
                pnl = (current_price - avg_price) * quantity
                pnl_percent = ((current_price / avg_price - 1) * 100) if avg_price > 0 else 0
                
                markdown += f"| {symbol} | {quantity} | ${avg_price:.2f} | ${current_price:.2f} | ${market_value:,.2f} | ${pnl:.2f} ({pnl_percent:+.2f}%) |\n"
            
            markdown += "\n"
        
        markdown += "## 📈 Market Data\n\n"
        
        # Add current market data
        current_prices = game_state.get('current_prices', {})
        if current_prices:
            markdown += "| Symbol | Open | High | Low | Close | Volume |\n"
            markdown += "|--------|------|------|-----|-------|--------|\n"
            
            for symbol, data in current_prices.items():
                if isinstance(data, dict):
                    open_price = data.get('open', 0)
                    high_price = data.get('high', 0)
                    low_price = data.get('low', 0)
                    close_price = data.get('close', 0)
                    volume = data.get('volume', 0)
                    
                    markdown += f"| {symbol} | ${open_price:.2f} | ${high_price:.2f} | ${low_price:.2f} | ${close_price:.2f} | {volume:,.0f} |\n"
            
            markdown += "\n"
        else:
            markdown += "*No market data available*\n\n"
        
        markdown += "## 📝 Transaction History\n\n"
        
        # Add transaction history
        transaction_history = game_state.get('transaction_history', [])
        if not transaction_history:
            markdown += "*No transactions yet*\n\n"
        else:
            markdown += "| Type | Symbol | Quantity | Price | Amount | P&L | Timestamp |\n"
            markdown += "|------|--------|----------|-------|--------|-----|-----------|\n"
            
            for transaction in transaction_history[-20:]:  # Show last 20 transactions
                trans_type = transaction.get('type', 'N/A')
                symbol = transaction.get('symbol', 'N/A')
                quantity = transaction.get('quantity', 0)
                price = transaction.get('price', 0)
                amount = transaction.get('amount', 0)
                pnl = transaction.get('profit_loss', 0)
                timestamp = transaction.get('timestamp', 'N/A')
                
                markdown += f"| {trans_type} | {symbol} | {quantity} | ${price:.2f} | ${amount:,.2f} | ${pnl:.2f} | {timestamp} |\n"
            
            if len(transaction_history) > 20:
                markdown += f"\n*... and {len(transaction_history) - 20} more transactions*\n"
            
            markdown += "\n"
        
        markdown += "## 🎯 Game Configuration\n\n"
        
        # Add game configuration
        config_fields = [
            ('initial_cash', 'Initial Cash'),
            ('current_date', 'Current Date'),
            ('current_stock', 'Current Stock'),
            ('train_start_date', 'Training Start Date'),
            ('train_end_date', 'Training End Date'),
        ]
        
        for field, label in config_fields:
            value = game_state.get(field, 'N/A')
            markdown += f"- **{label}**: {value}\n"
        
        markdown += "\n## 📊 K-line Data for AI\n\n"
        
        # Add K-line data for AI
        kline_fields = [
            ('current_day_k_observing', 'Daily K-line'),
            ('current_week_k_observing', 'Weekly K-line'),
            ('current_month_k_observing', 'Monthly K-line'),
        ]
        
        for field, label in kline_fields:
            value = game_state.get(field, '')
            if value and value != '股票走势:':
                markdown += f"### {label}\n\n```\n{value}\n```\n\n"
        
        markdown += f"---\n*Generated by GameStateManager v{self.version} at {timestamp}*\n"
        
        return markdown
    
    def _parse_markdown_content(self, content: str) -> Optional[Dict[str, Any]]:
        """
        Parse Markdown content back to game state
        
        Args:
            content: Markdown content string
            
        Returns:
            Game state dictionary or None if parsing fails
        """
        try:
            # Extract basic info
            lines = content.split('\n')
            game_info = {}
            
            # Parse game information
            for line in lines:
                if line.startswith('- **Game ID**:'):
                    game_info['game_id'] = line.split(': ')[1].strip()
                elif line.startswith('- **Current Stock**:'):
                    game_info['current_stock'] = line.split(': ')[1].strip()
                elif line.startswith('- **Current Date**:'):
                    game_info['current_date'] = line.split(': ')[1].strip()
            
            # This is a simplified parser - in a real implementation,
            # you might want to use a proper Markdown parser
            # For now, we'll return basic info
            return {
                'game_info': game_info,
                'raw_content': content,
                'parsed_at': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            
        except Exception as e:
            print(f"Error parsing Markdown content: {e}")
            return None
    
    def _extract_basic_info(self, content: str) -> Dict[str, Any]:
        """
        Extract basic information from Markdown content
        
        Args:
            content: Markdown content string
            
        Returns:
            Dictionary with basic info
        """
        basic_info = {}
        
        lines = content.split('\n')
        for line in lines:
            if line.startswith('- **Game ID**:'):
                basic_info['game_id'] = line.split(': ')[1].strip()
            elif line.startswith('- **Current Stock**:'):
                basic_info['current_stock'] = line.split(': ')[1].strip()
            elif line.startswith('- **Current Date**:'):
                basic_info['current_date'] = line.split(': ')[1].strip()
            elif line.startswith('- **Auto Save**:'):
                basic_info['auto_save'] = line.split(': ')[1].strip()
        
        return basic_info
    
    def create_backup(self, game_id: str) -> str:
        """
        Create a backup of the latest game state
        
        Args:
            game_id: Game ID to backup
            
        Returns:
            Path to the backup file
        """
        # Load latest state
        game_state = self.load_game_state(game_id, use_latest=True)
        if not game_state:
            raise ValueError(f"No game state found for {game_id}")
        
        # Create backup with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_filename = f"game_state_{game_id}_backup_{timestamp}.md"
        backup_filepath = self.save_dir / backup_filename
        
        # Create backup content
        backup_content = self._generate_markdown_content(
            game_state, game_id, False
        )
        
        # Write backup file
        with open(backup_filepath, 'w', encoding='utf-8') as f:
            f.write(backup_content)
        
        return str(backup_filepath)
    
    def cleanup_old_files(self, game_id: Optional[str] = None, 
                         keep_latest: int = 10) -> int:
        """
        Clean up old game state files
        
        Args:
            game_id: Game ID to clean up, None for all games
            keep_latest: Number of latest files to keep
            
        Returns:
            Number of files deleted
        """
        if game_id:
            pattern = f"game_state_{game_id}_*.md"
            files = list(self.save_dir.glob(pattern))
        else:
            pattern = "game_state_*.md"
            files = list(self.save_dir.glob(pattern))
        
        if len(files) <= keep_latest:
            return 0
        
        # Sort by modification time (newest first)
        files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
        
        # Delete oldest files
        deleted_count = 0
        for filepath in files[keep_latest:]:
            filepath.unlink()
            deleted_count += 1
        
        return deleted_count


# Example usage and testing
if __name__ == '__main__':
    # Create GameStateManager
    manager = GameStateManager("./test_game_states")
    
    # Test game state
    test_game_state = {
        'cash_balance': 50000.0,
        'portfolio': {
            'sh.600000': {
                'symbol': 'sh.600000',
                'quantity': 1000,
                'avg_price': 10.50,
                'timestamp': '2025-01-01 10:00:00'
            }
        },
        'transaction_history': [
            {
                'type': 'BUY',
                'symbol': 'sh.600000',
                'quantity': 1000,
                'price': 10.50,
                'amount': 10500.0,
                'profit_loss': 0,
                'timestamp': '2025-01-01 10:00:00'
            }
        ],
        'current_prices': {
            'sh.600000': {
                'open': 10.50,
                'high': 11.00,
                'low': 10.40,
                'close': 10.80,
                'volume': 1000000
            }
        },
        'current_date': '2025-01-01 10:00:00',
        'current_stock': 'sh.600000',
        'initial_cash': 50000.0
    }
    
    # Test saving
    print("Testing game state saving...")
    saved_file = manager.save_game_state(test_game_state, "test_game")
    print(f"Saved to: {saved_file}")
    
    # Test loading
    print("\nTesting game state loading...")
    loaded_state = manager.load_game_state("test_game")
    print(f"Loaded state: {loaded_state}")
    
    # Test listing
    print("\nTesting game state listing...")
    game_states = manager.list_game_states()
    print(f"Found {len(game_states)} game states")
    for state in game_states:
        print(f"  - {state['game_id']}: {state['timestamp']}")
    
    # Test cleanup
    print("\nTesting cleanup...")
    deleted = manager.cleanup_old_files("test_game", keep_latest=5)
    print(f"Deleted {deleted} old files")
    
    print("\n✅ GameStateManager test completed!")