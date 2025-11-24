import asyncio
import copy
import json
import logging
import os
import subprocess
import time
import typing
import sys
import ctypes
import math
from asyncio import StreamReader, StreamWriter
from typing import List
import shutil

import Utils
from Utils import async_start
from CommonClient import CommonContext, server_loop, gui_enabled, console_loop, ClientCommandProcessor, logger, \
    get_base_parser
from NetUtils import NetworkItem, NetworkPlayer, NetworkSlot, SlotType

# GDB reader will be imported after game path is set
GDBReader = None

SYSTEM_MESSAGE_ID = 0

def get_game_documents_folder():
    """Find the game documents folder, checking both German and English folder names."""
    documents_dir = os.path.join(os.path.expanduser("~"), "Documents")
    possible_folders = [
        "DIE SIEDLER - DEdk",
        "THE SETTLERS - HoK",
        "The Settlers - Heritage of Kings"
    ]
    
    for folder_name in possible_folders:
        folder_path = os.path.join(documents_dir, folder_name)
        if os.path.exists(folder_path):
            return folder_name
    
    # If none exist, return the German version as default (will be created)
    return "DIE SIEDLER - DEdk"

CONNECTION_TIMING_OUT_STATUS = "Connection timing out. Please restart your game, then restart connector_settlers.lua"
CONNECTION_REFUSED_STATUS = "Connection Refused. Please start your game and make sure connector_settlers.lua is running"
CONNECTION_RESET_STATUS = "Connection was reset. Please restart your game, then restart connector_settlers.lua"
CONNECTION_TENTATIVE_STATUS = "Initial Connection Made"
CONNECTION_CONNECTED_STATUS = "Connected"
CONNECTION_INITIAL_STATUS = "Connection has not been initiated"

DISPLAY_MSGS = True

# These will be populated from the server
item_ids = {}
location_ids = {}
items_by_id = {}
locations_by_id = {}

class SettlersCommandProcessor(ClientCommandProcessor):

    def _cmd_game(self):
        """Check Game Connection State"""
        if isinstance(self.ctx, SettlersContext):
            logger.info(f"Game Status: {self.ctx.game_status}")
            
    def _cmd_game_path(self):
        """Set or display the game installation path"""
        if self.ctx.game_path:
            logger.info(f"Current game path: {self.ctx.game_path}")
        else:
            logger.info("Game path not set")
        return True

    def _cmd_toggle_msgs(self):
        """Toggle displaying messages in the game"""
        global DISPLAY_MSGS
        DISPLAY_MSGS = not DISPLAY_MSGS
        logger.info(f"Messages are now {'enabled' if DISPLAY_MSGS else 'disabled'}")


class SettlersContext(CommonContext):
    command_processor = SettlersCommandProcessor
    items_handling = 0b111  # full item handling
    game = "SettlersHeritageOfKings"

    def __init__(self, server_address, password):
        super().__init__(server_address, password)
        self.bonus_items = []
        self.messages = {}
        self.locations_array = None
        self.game_status = CONNECTION_INITIAL_STATUS
        self.game_path = None
        self.gdb_path = None
        self.slot_data = dict()
        self.item_values = {}  # Store item values (0 = not exists, 1 = exists, >1 = progressive)
        self.location_values = {}  # Store location values (0 = not checked, 1 = checked)
        self.game_sync_task = None
        # Initialize items and locations dictionaries
        self.items = {}
        self.locations = {}
        self.missing_locations = set()
        self.locations_checked = []  # Changed from set to list
        self.items_received = []
        self.offset_50 = 0x0000005E
        self.savegames_appended_until = 0  # number of received items already reflected in SaveGames folder name
        
        # Load saved game path if it exists
        self.load_game_path()
        
        # Import necessary types
        from NetUtils import NetworkItem, NetworkPlayer, NetworkSlot, SlotType

    def get_item_count_for_id(self, item_id: int) -> int:
        """Return how many times the given item id is present for the current player."""
        count = 1
            # Also check current GDB value and add it
        item_name = items_by_id.get(item_id)
        if item_name:
            current_gdb_value = self.get_value(item_name)
            if current_gdb_value > 0:
                count += current_gdb_value
        return count

    def append_item_to_savegames_folder(self, item_id: int):
        try:
            item_name = items_by_id.get(item_id)
            if not item_name:
                return
            # Count current value for this item for the current player
            current_value = self.get_item_count_for_id(item_id)
            # Build segment
            segment = f"{item_name}.{current_value}-"
            # Resolve Documents\<Game Folder>\SaveGames
            documents_dir = os.path.join(os.path.expanduser("~"), "Documents")
            game_folder = get_game_documents_folder()
            savegames_base = os.path.join(documents_dir, game_folder, "SaveGames")
            os.makedirs(savegames_base, exist_ok=True)
            prefix = "__archipelago-"
            candidates = [d for d in os.listdir(savegames_base) if d.startswith(prefix) and os.path.isdir(os.path.join(savegames_base, d))]
            if candidates:
                current_name = max(candidates, key=lambda d: os.path.getmtime(os.path.join(savegames_base, d)))
                current_path = os.path.join(savegames_base, current_name)
                
                # Check how many items are already in the folder name
                # Count segments that match pattern "itemname.number-"
                import re
                item_segments = re.findall(r'[^.-]+\.\d+-', current_name)
                if len(item_segments) >= 6:
                    # Reset to base archipelago folder
                    new_name = "__archipelago-"
                    new_path = os.path.join(savegames_base, new_name)
                    os.rename(current_path, new_path)
                    current_name = new_name
                    current_path = new_path
                    logger.info("Reset SaveGames folder to __archipelago- (6+ items reached)")
            else:
                current_name = "__archipelago-"
                current_path = os.path.join(savegames_base, current_name)
                os.makedirs(current_path, exist_ok=True)
            
            # Only append if this exact segment is not already present
            if current_name.endswith(segment):
                return
            if f"-{segment}" in current_name or current_name.endswith(segment):
                return
            new_name = current_name + segment
            new_path = os.path.join(savegames_base, new_name)
            # Rename the folder
            os.rename(current_path, new_path)
        except Exception as e:
            logger.error(f"Failed to update SaveGames folder name: {e}")

    def reset_savegames_folder(self):
        """Reset the SaveGames folder to __archipelago-"""
        try:
            # Resolve Documents\<Game Folder>\SaveGames
            documents_dir = os.path.join(os.path.expanduser("~"), "Documents")
            game_folder = get_game_documents_folder()
            savegames_base = os.path.join(documents_dir, game_folder, "SaveGames")
            os.makedirs(savegames_base, exist_ok=True)
            prefix = "__archipelago-"
            
            # Find existing archipelago folder
            candidates = [d for d in os.listdir(savegames_base) if d.startswith(prefix) and os.path.isdir(os.path.join(savegames_base, d))]
            if candidates:
                current_name = candidates[0]
                current_path = os.path.join(savegames_base, current_name)
                new_path = os.path.join(savegames_base, prefix)
                os.rename(current_path, new_path)
        except Exception as e:
            logger.error(f"Failed to reset SaveGames folder: {e}")

    def save_game_path(self):
        """Save the game path to a JSON file."""
        if self.game_path:
            config = {
                "game_path": self.game_path,
            }
            config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "settlers_config.json")
            try:
                with open(config_path, "w") as f:
                    json.dump(config, f)
                logger.info(f"Saved game path to {config_path}")
            except Exception as e:
                logger.error(f"Failed to save game path: {e}")

    def load_game_path(self):
        """Load the game path from the JSON file."""
        config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "settlers_config.json")
        try:
            if os.path.exists(config_path):
                with open(config_path, "r") as f:
                    config = json.load(f)
                if "game_path" in config and os.path.exists(config["game_path"]):
                    self.game_path = config["game_path"]
                    logger.info(f"Loaded game path from {config_path}")
        except Exception as e:
            logger.error(f"Failed to load game path: {e}")

    def get_value(self, key):
        """Returns the value for a specific key."""
        try:
            # Read the file content
            with open(self.gdb_path, 'rb') as f:
                content = f.read()
            
            # Find the last FF FD FF FD
            last_ff_fd = content.rfind(b'\xff\xfd\xff\xfd')
            if last_ff_fd == -1:
                return 0
                
            # Find the second to last FF FD FF FD
            second_last_ff_fd = content.rfind(b'\xff\xfd\xff\xfd', 0, last_ff_fd)
            if second_last_ff_fd == -1:
                return 0
            
            # Search only in the area between the second to last and the last FF FD FF FD
            search_content = content[second_last_ff_fd:last_ff_fd]
            
            key_bytes = key.encode('latin-1')
            key_pos = search_content.find(key_bytes)
            
            if key_pos != -1:
                # Key found, search for the pattern 00 03 00 02 00 00 00
                pattern = bytes([0x00, 0x03, 0x00, 0x02, 0x00, 0x00, 0x00])
                pattern_pos = search_content.find(pattern, key_pos + len(key_bytes))

                if pattern_pos != -1:
                    # Pattern found, the value is the next byte
                    # The value is stored as 0x30 + value, so we need to subtract 0x30
                    value_byte = search_content[pattern_pos + 7]
                    value = value_byte - 0x30
                    return value
            
            return 0
            
        except Exception as e:
            logger.error(f"Error reading file: {e}")
            return 0
        
    def set_value(self, key, value):
        """Sets a value for a specific key."""
        try:
            # Read the file content
            with open(self.gdb_path, 'rb') as f:
                content = bytearray(f.read())
            
            # Find the last FF FD FF FD marker
            last_ff_fd = content.rfind(b'\xff\xfd\xff\xfd')
            if last_ff_fd == -1:
                logger.error("Error: No FF FD FF FD marker found")
                return
                
            # Find the second to last FF FD FF FD
            second_last_ff_fd = content.rfind(b'\xff\xfd\xff\xfd', 0, last_ff_fd)
            if second_last_ff_fd == -1:
                logger.error("Error: No second FF FD FF FD marker found")
                return
                
            # The data section starts 8 bytes after the second to last FF FD FF FD
            data_start = second_last_ff_fd + 4
            
            # Find the next valid entry after data_start
            pos = data_start
            while pos < last_ff_fd:
                if content[pos] > 0:  # Found a non-zero byte
                    break
                pos += 1
            
            # Clean up the area between data_start and the next valid entry
            content = content[:data_start] + content[pos:]
            last_ff_fd = content.rfind(b'\xff\xfd\xff\xfd')  # Update last_ff_fd position
            data_end = last_ff_fd
            
            # First, check if the key exists and get its position
            key_bytes = key.encode('latin-1')
            pos = data_start
            entry_found = False
            entry_start = 0
            entry_end = 0
            
            while pos < data_end:
                try:
                    # Skip any invalid bytes until we find a valid entry start
                    while pos < data_end and content[pos] == 0xff:
                        pos += 1
                        
                    if pos >= data_end:
                        break
                        
                    # Each entry should start with a length byte followed by 3 null bytes
                    length_byte = content[pos]
                    if length_byte == 0 or pos + 4 >= data_end:
                        pos += 1
                        continue
                        
                    # Skip the 3 null bytes
                    pattern_start = pos + 4
                    
                    # Find the next FF FD marker
                    next_marker = content.find(b'\xff\xfd', pattern_start)
                    if next_marker == -1 or next_marker > data_end:
                        pos += 1
                        continue
                        
                    # Extract the key bytes
                    key_length = length_byte - 1  # Subtract 1 for the null terminator
                    entry_key_bytes = content[pattern_start:pattern_start + key_length]
                    
                    # Compare the key bytes directly
                    if entry_key_bytes == key_bytes:
                        entry_found = True
                        entry_start = pos
                        entry_end = next_marker + 2
                        break
                        
                    pos = next_marker + 2
                        
                except Exception as e:
                    logger.error(f"Error parsing entry at position {pos}: {e}")
                    pos += 1
            
            if entry_found:
                # Find the value pattern in the existing entry
                value_pattern = bytes([0x00, 0x03, 0x00, 0x02, 0x00, 0x00, 0x00])
                value_pos = content[entry_start:entry_end].find(value_pattern)
                
                if value_pos != -1:
                    # Update only the value byte
                    content[entry_start + value_pos + 7] = 0x30 + value
                    # Write the changes back to the file
                    with open(self.gdb_path, 'wb') as f:
                        f.write(content)
                    return
            
            # If we get here, the key doesn't exist, so create a new entry
            value_pattern = bytearray([0x00, 0x03, 0x00, 0x02, 0x00, 0x00, 0x00, 0x30 + value, 0x00])
            new_entry = bytes([len(key) + 1, 0, 0, 0]) + key_bytes + value_pattern
            
            # Find all valid entries for sorting
            entries = []
            pos = data_start
            
            while pos < data_end:
                try:
                    # Skip any invalid bytes until we find a valid entry start
                    while pos < data_end and content[pos] == 0xff:
                        pos += 1
                        
                    if pos >= data_end:
                        break
                        
                    # Each entry should start with a length byte followed by 3 null bytes
                    length_byte = content[pos]
                    if length_byte == 0 or pos + 4 >= data_end:
                        pos += 1
                        continue
                        
                    # Skip the 3 null bytes
                    pattern_start = pos + 4
                    
                    # Find the next FF FD marker
                    next_marker = content.find(b'\xff\xfd', pattern_start)
                    if next_marker == -1 or next_marker > data_end:
                        pos += 1
                        continue
                        
                    # Extract everything between pattern_start and next_marker
                    entry_data = content[pattern_start:next_marker]
                    
                    # Try to decode as Latin-1 and remove any control characters
                    try:
                        entry_key = ''.join(chr(b) for b in entry_data if b >= 32 and b < 127).strip()
                        if entry_key:  # Only add non-empty keys
                            # Include the entire entry in the tuple, but without the FF FD marker
                            entry_content = content[pos:next_marker]
                            entries.append((entry_key, entry_content))
                    except:
                        pass
                        
                    pos = next_marker + 2
                        
                except Exception as e:
                    logger.error(f"Error parsing entry at position {pos}: {e}")
                    pos += 1
            
            # Add the new entry to the list
            entries.append((key, new_entry))
            
            # Sort all entries alphabetically
            entries.sort(key=lambda x: x[0].lower())
            
            # Rebuild the entire data section in sorted order
            new_content = bytearray(content[:data_start])
            
            # Add all entries in sorted order, with FF FD markers between them
            for i, (_, entry_content) in enumerate(entries):
                new_content.extend(entry_content)
                if i < len(entries) - 1:  # Add FF FD marker between entries
                    new_content.extend(b'\xff\xfd')
            
            # Add the final FF FD FF FD marker
            new_content.extend(b'\xff\xfd\xff\xfd')
            
            # Add any remaining content after the last FF FD FF FD
            if last_ff_fd + 4 < len(content):
                new_content.extend(content[last_ff_fd + 4:])
            
            # Increment the counter only for new entries
            self.increment_counter(new_content)
            
            # Write the changes back to the file
            with open(self.gdb_path, 'wb') as f:
                f.write(new_content)
            
        except Exception as e:
            logger.error(f"Error writing to file: {e}")

    def increment_counter(self, content):
        """Increments the counter at offset 0x0000005E and checks if the next digit needs to be incremented."""
        if self.offset_50 + 4 <= len(content):
            current_value = int.from_bytes(content[self.offset_50:self.offset_50+4], byteorder='little', signed=True)
            new_value = current_value + 1
            content[self.offset_50:self.offset_50+4] = new_value.to_bytes(4, byteorder='little', signed=True)
            
            # Check if the digit is full (e.g., if the value reaches 255)
            if new_value >= 255:
                self.offset_50 += 4  # Go to the next digit
                logger.info(f"Counter at offset {self.offset_50} incremented.")

    async def server_auth(self, password_requested: bool = False):
        if password_requested and not self.password:
            await super(SettlersContext, self).server_auth(password_requested)
            
        await self.get_username()
        await self.send_connect()
        
    async def get_username(self):
        if not self.auth:
            self.auth = self.username
            if not self.auth:
                logger.info('Enter slot name:')
                self.auth = await self.console_input()
                
    async def send_connect(self):
        """Send connection information to the server"""
        if not self.auth:
            logger.error("No username set. Cannot connect to server.")
            return

        # Create a payload with game information
        payload = {
            'cmd': 'Connect',
            'password': self.password,
            'name': self.auth,
            'version': Utils.version_tuple,
            'tags': self.tags,
            'items_handling': self.items_handling,
            'uuid': Utils.get_unique_identifier(),
            'game': self.game,
            'slot_data': True
        }
        
        # Send the connect packet to the server
        await self.send_msgs([payload])
        # Request DataPackage and race mode
        await self.send_msgs([
            {"cmd": "Get", "keys": ["_read_race_mode"]},
            {"cmd": "GetDataPackage"}
        ])
        
        logger.info("Sent connection information to server")
        
    async def get_game_path(self) -> str:
        """Ask for the game installation path if not already set."""
        if not self.game_path:
            if self.ui:
                self.ui.focus_textinput()
            logger.info("Please enter the full path to your Settlers Heritage of Kings installation:")
            self.game_path = await self.console_input()
            
            # Validate the path
            if not os.path.exists(self.game_path):
                logger.error(f"Path does not exist: {self.game_path}")
                self.game_path = None
                return await self.get_game_path()
                
            # Set GDB path
            game_folder = get_game_documents_folder()
            self.gdb_path = os.path.join(os.path.expanduser("~"), "Documents", game_folder, "Data", "GDB.bin")
            
            # Check if GDB file exists
            if not os.path.exists(self.gdb_path):
                logger.error(f"GDB file not found at: {self.gdb_path}")
                self.game_path = None
                return await self.get_game_path()
                
            # Check file permissions
            try:
                # Test read access
                with open(self.gdb_path, 'rb') as f:
                    f.read(1)
                
                # Test write access
                with open(self.gdb_path, 'ab') as f:
                    f.write(b'')
                
            except (PermissionError, OSError) as e:
                logger.error(f"Cannot access GDB file. Please run as administrator or check permissions: {self.gdb_path}")
                logger.error(f"Error: {str(e)}")
                self.game_path = None
                return await self.get_game_path()

        else:
            # If game_path is already set, make sure gdb_path is also set
            if not self.gdb_path:
                game_folder = get_game_documents_folder()
                self.gdb_path = os.path.join(os.path.expanduser("~"), "Documents", game_folder, "Data", "GDB.bin")
                
            # Verify GDB file still exists and is accessible
            if not os.path.exists(self.gdb_path):
                logger.error(f"GDB file not found at: {self.gdb_path}")
                self.game_path = None
                return await self.get_game_path()
                
            try:
                # Test read access
                with open(self.gdb_path, 'rb') as f:
                    f.read(1)
                
                # Test write access
                with open(self.gdb_path, 'ab') as f:
                    f.write(b'')
                
            except (PermissionError, OSError) as e:
                logger.error(f"Cannot access GDB file. Please run as administrator or check permissions: {self.gdb_path}")
                logger.error(f"Error: {str(e)}")
                self.game_path = None
                return await self.get_game_path()
                
        # Set file_path to gdb_path for compatibility with existing code
        self.file_path = self.gdb_path
        return self.game_path

    def _set_message(self, msg: str, msg_id: int):
        if DISPLAY_MSGS:
            self.messages[(time.time(), msg_id)] = msg

    def on_package(self, cmd: str, args: dict):
        global item_ids, location_ids, items_by_id, locations_by_id
        
        if cmd == 'Connected':
            self.slot_data = args.get("slot_data", {})
            logger.debug(f"Received slot_data: {self.slot_data}")
            
            # Update tab visibility when connected
            if self.ui:
                self.ui.update_tab_visibility()
                
            # Create a task to handle the initialization sequence
            async def initialize_sequence():
                # First get the game path and initialize GDB reader
                await self.get_game_path()
                
                # Request received items and checked locations from server
                await self.send_msgs([
                    {"cmd": "Get", "keys": ["received_items"]},
                ])

                self.locations_checked = args.get("checked_locations", [])
            
            # Start the initialization sequence
            asyncio.create_task(initialize_sequence())
            
        elif cmd == 'ReceivedItems':
            # Handle received items
            start_index = args["index"]
            if start_index == 0:
                self.items_received = []
                # Do not append historical items to folder name during a full sync
                self.savegames_appended_until = 0
            elif start_index != len(self.items_received):
                # Request sync if we're missing items
                asyncio.create_task(self.send_msgs([{"cmd": "Sync"}]))
            
            # Process new items
            for offset, item in enumerate(args["items"]):
                try:
                    network_item = NetworkItem(*item)
                    self.items_received.append(network_item)
                    # Only append truly new items (skip initial full history at index 0)
                    item_global_index = start_index + offset
                    if start_index != 0 and item_global_index >= self.savegames_appended_until:
                        self.append_item_to_savegames_folder(network_item.item)
                        item_name = items_by_id.get(network_item.item)
                        if item_name:
                            value = self.get_item_count_for_id(network_item.item)
                except Exception as e:
                    logger.error(f"Error processing received item: {e}")
            # Advance the watermark for appended items
            self.savegames_appended_until = max(self.savegames_appended_until, start_index + len(args["items"]))
                
        elif cmd == 'LocationChecks':
            # Handle checked locations
            locations = args.get("locations", [])
            logger.debug(f"Received LocationChecks with locations: {locations}")
            for location in locations:
                try:
                    if location not in self.locations_checked:
                        self.locations_checked.append(location)
                    # Update GDB file with the checked location
                    location_name = locations_by_id.get(location)
                    if location_name:
                        self.set_value(location_name, 1)
                except Exception as e:
                    logger.error(f"Error processing checked location: {e}")
                    
        elif cmd == 'Print':
            msg = args['text']
            if ': !' not in msg:
                self._set_message(msg, SYSTEM_MESSAGE_ID)

        elif cmd == 'DataPackage':
            # Get items and locations from the DataPackage
            game_data = args["data"]["games"][self.game]
            
            # Clear existing maps
            item_ids.clear()
            location_ids.clear()
            items_by_id.clear()
            locations_by_id.clear()
            
            # Get items from the DataPackage
            for item_name, item_id in game_data["item_name_to_id"].items():
                item_ids[item_name] = item_id
                items_by_id[item_id] = item_name
                
            # Get locations from the DataPackage
            for location_name, location_id in game_data["location_name_to_id"].items():
                location_ids[location_name] = location_id
                locations_by_id[location_id] = location_name

        elif cmd == 'Retrieved':
            # Handle retrieved data from Get command
                      # Re-initialize GDB with updated locations
            if item_ids and location_ids:
                process_data(self)

        elif cmd == 'ConnectionRefused':
            # Update tab visibility when connection is refused
            if self.ui:
                self.ui.update_tab_visibility()

    def on_print_json(self,args: dict):
        if self.ui:
            self.ui.print_json(copy.deepcopy(args["data"]))
        else:
            text = self.jsontotextparser(copy.deepcopy(args["data"]))
        relevant = args.get("type", None) in {"Hint", "ItemSend"}
        if relevant:
            item = args["item"]
            # goes to self world
            if self.slot_concerns_self(args["receiving"]):
                relevant = True
            # found in self world
            elif self.slot_concerns_self(item.player):
                relevant = True
            # not related
            else:
                relevant = False
            if relevant:
                item = args["item"]
                msg = self.raw_text_parser(copy.deepcopy(args["data"]))
                self._set_message(msg, item.item)

    def run_gui(self):
        from kvui import GameManager
        from kivy.uix.tabbedpanel import TabbedPanel, TabbedPanelItem
        from kivy.uix.gridlayout import GridLayout
        from kivy.uix.button import Button
        from kivymd.uix.tab import MDTabsItem, MDTabsItemText
        from kivy.uix.boxlayout import BoxLayout
        from kivy.uix.checkbox import CheckBox
        from kivy.uix.label import Label
        from kivy.uix.scrollview import ScrollView

        class SettlersManager(GameManager):
            logging_pairs = [
                ("Client", "Archipelago"),
                ("GamePath", "Game Path")
            ]
            base_title = "Archipelago Settlers Heritage of Kings Client"

            def build(self):
                result = super().build()
                
                # Create MainCampaign tab content
                grid = GridLayout(cols=4, spacing=20, padding=10)
                for i in range(1, 17):
                    button = Button(text=f"Mission {i}", size_hint=(None, None), size=(150, 60))
                    if i == 1:
                        button.text = "Thalgrund"
                    elif i == 2:
                        button.text = "Village Attack"
                    elif i == 3:
                        button.text = "Crawford"
                    elif i == 4:
                        button.text = "Cleycourt"
                    elif i == 5:
                        button.text = "Flood"
                    elif i == 6:
                        button.text = "Barmecia"
                    elif i == 7:
                        button.text = "Folklung"
                    elif i == 8:
                        button.text = "Norfolk"
                    elif i == 9:
                        button.text = "Kaloix"
                    elif i == 10:
                        button.text = "Plague"
                    elif i == 11:
                        button.text = "OldKingsCastle"
                    elif i == 12:
                        button.text = "Cloudy Mountains"
                    elif i == 13:
                        button.text = "Evelance"
                    elif i == 14:
                        button.text = "Wasteland"
                    elif i == 15:
                        button.text = "Battle for Evelance"
                    elif i == 16:
                        button.text = "Main Client"

                    button.bind(on_press=lambda instance, mission=i: self.on_main_campaign_button_press(mission))
                    grid.add_widget(button)
                
                # Add MainCampaign tab
                self.main_campaign_tab = self.add_client_tab("MainCampaign", grid)
                # Initially hide the tab
                self.main_campaign_tab.disabled = True

                return result

            def on_main_campaign_button_press(self, level_id):
                if not self.ctx.game_path:
                    logger.error("Game path not set")
                    return
                    
                lvlstring = "-extra2 -scewindow"
                if level_id == 1:
                    lvlstring = '-extra2 -MAP:"01_thalgrund_archipelago" -scewindow'
                elif level_id == 2:
                    lvlstring = '-extra2 -MAP:"02_villageattack_archipelago" -scewindow'
                elif level_id == 3:
                    lvlstring = '-extra2 -MAP:"04_crawford_archipelago" -scewindow'
                elif level_id == 4:
                    lvlstring = '-extra2 -MAP:"06_cleycourt_archipelago" -scewindow'
                elif level_id == 5:
                    lvlstring = '-extra2 -MAP:"07_flood_archipelago" -scewindow'
                elif level_id == 6:
                    lvlstring = '-extra2 -MAP:"08_barmecia_archipelago" -scewindow'
                elif level_id == 7:
                    lvlstring = '-extra2 -MAP:"10_folklung_archipelago" -scewindow'
                elif level_id == 8:
                    lvlstring = '-extra2 -MAP:"11_norfolk_archipelago" -scewindow'
                elif level_id == 9:
                    lvlstring = '-extra2 -MAP:"12_kaloix_archipelago" -scewindow'
                elif level_id == 10:
                    lvlstring = '-extra2 -MAP:"13_plague_archipelago" -scewindow'
                elif level_id == 11:
                    lvlstring = '-extra2 -MAP:"15_oldkingscastle_archipelago" -scewindow'
                elif level_id == 12:
                    lvlstring = '-extra2 -MAP:"17_cloudymountains_archipelago" -scewindow'
                elif level_id == 13:
                    lvlstring = '-extra2 -MAP:"18_evelance_archipelago" -scewindow'
                elif level_id == 14:
                    lvlstring = '-extra2 -MAP:"19_wasteland_archipelago" -scewindow'
                elif level_id == 15:
                    lvlstring = '-extra2 -MAP:"20_battleofevelance_archipelago" -scewindow'
                    
            
                logger.info(f"Starting Level {level_id}...")
                process_data(self.ctx)
                    
                game_exe = os.path.join(self.ctx.game_path, "bin", "settlershok.exe")
                os.chdir(os.path.dirname(game_exe))
                
                command = f'"{game_exe}" {lvlstring}'
                subprocess.Popen(command, shell=True)

            def update_tab_visibility(self):
                # Update tab visibility based on connection status
                if hasattr(self, 'main_campaign_tab'):
                    self.main_campaign_tab.disabled = not self.ctx.server_task or self.ctx.server_task.done()

        self.ui = SettlersManager(self)
        self.ui_task = asyncio.create_task(self.ui.async_run(), name="UI")

    async def connect(self, address: typing.Optional[str] = None) -> None:
        """ disconnect any previous connection, and open new connection to the server """
        if self.server_task:
            self.server_task.cancel()
            try:
                await self.server_task
            except asyncio.CancelledError:
                pass
            self.server_task = None
            
        if self.autoreconnect_task:
            self.autoreconnect_task.cancel()
            try:
                await self.autoreconnect_task
            except asyncio.CancelledError:
                pass
            self.autoreconnect_task = None
            
        # Clean up the address by removing any quotes
        if address:
            address = address.strip("'\"")
            
        self.server_task = asyncio.create_task(server_loop(self, address), name="server loop")


def get_payload(ctx: SettlersContext):
    current_time = time.time()
    bonus_items = [item for item in ctx.items_received]
    return json.dumps(
        {
            "items": [item.item for item in ctx.items_received],
            "messages": {f'{key[0]}:{key[1]}': value for key, value in ctx.messages.items()
                         if key[0] > current_time - 10},
            "bonusItems": bonus_items
        }
    )


def process_data(ctx: SettlersContext):
    # Count items per ID for current player
    item_counts = {}
    for item in ctx.items_received:
        if item.player != 0:  # Only count items for current player
            if item.item in item_counts:
                item_counts[item.item] += 1
            else:
                item_counts[item.item] = 1

    # Initialize all locations in GDB based on server data
    for location_id in location_ids.values():
        try:
            location_name = locations_by_id.get(location_id)
            if location_name:
                # Set value to 1 if location is checked on server, 0 otherwise
                value = 1 if location_id in ctx.locations_checked else 0
                ctx.set_value(location_name, value)
        except Exception as e:
            logger.error(f"Error initializing location {location_name}: {e}")

    ctx.set_value("starting_hero",get_starting_hero(ctx.slot_data["starting_hero"]))
    difficulty = ctx.slot_data["difficulty"]
    ctx.set_value("difficulty",difficulty)
    ctx.set_value("player_color",ctx.slot_data["player_color"])
    ctx.set_value("game_speed",ctx.slot_data["game_speed"])

    # Progression Difficulty Balancing
    if ctx.slot_data["progression_difficulty"] == 1:
        progression_status = len(item_counts)/len(item_ids)
        if difficulty == 1:
            progression_status = math.floor(progression_status * 2)
        elif difficulty == 2:
            progression_status = math.floor(progression_status * 3)
        else:
            progression_status = math.floor(progression_status * 4)
    else:
        progression_status = 0

    ctx.set_value("progression",progression_status)

    # Initialize all items in GDB based on server data
    for item_id in item_ids.values():
        try:
            item_name = items_by_id.get(item_id)
            if item_name:
                # Get base count from received items
                value = item_counts.get(item_id, 0)

                # Add +1 if item is in starting_unit
                if "starting_unit" in ctx.slot_data and ctx.slot_data["starting_unit"] != "disabled":
                    unit_name = f"progressive_{ctx.slot_data['starting_unit']}"
                    if item_name == unit_name:
                        value += 1

                ctx.set_value(item_name, value)
        except Exception as e:
            logger.error(f"Error initializing item {item_name}: {e}")

    # Reset SaveGames folder after saving to GDB
    ctx.reset_savegames_folder()

def get_starting_hero(starting_hero):
    heroId = 0
    match starting_hero:
        case "dario":
            heroId = 1
        case "pilgrim":
            heroId = 2
        case "salim":
            heroId = 3
        case "erec":
            heroId = 4
        case "ari":
            heroId = 5
        case "helias":
            heroId = 6
        case "kerberos":
            heroId = 7
        case "mary":
            heroId = 8
        case "varg":
            heroId = 9
        case "drake":
            heroId = 10
        case "yuki":
            heroId = 11
        case "kala":
            heroId = 12

    return heroId



async def game_sync_task(ctx: SettlersContext):
    """Synchronize game state with the GDB file"""
    
    while not ctx.exit_event.is_set():
        try:
            if not ctx.gdb_path:
                await asyncio.sleep(1)
                continue
                
            # Check all items for changes
            for item_name, item_id in item_ids.items():
                try:
                    # Get current value from GDB
                    current_value = ctx.get_value(item_name)
                    previous_value = ctx.item_values.get(item_name, 0)
                    
                    # If value has changed
                    if current_value != previous_value:
                        ctx.item_values[item_name] = current_value
                        
                        # If this is a new item (value > 0)
                        if current_value > 0 and item_name not in ctx.items_received:
                            # Create a NetworkItem for this item
                            from NetUtils import NetworkItem
                            network_item = NetworkItem(item_id, ctx.slot, 0)
                            ctx.items_received.append(network_item)
                            
                            # Notify the server
                        await ctx.send_msgs([
                                {"cmd": "ItemReceived", 
                                 "item": network_item}
                            ])
                except Exception as e:
                    logger.error(f"Error checking item {item_name}: {e}")
                    
            # Check all locations for changes
            for location_name, location_id in location_ids.items():
                try:
                    # Get current value from GDB
                    current_value = ctx.get_value(location_name)
                    previous_value = ctx.location_values.get(location_name, 0)
                    
                    # If value has changed
                    if current_value != previous_value:
                        ctx.location_values[location_name] = current_value
                        
                        # If this is a checked location (value > 0)
                        if current_value > 0 and location_id not in ctx.locations_checked:
                            ctx.locations_checked.append(location_id)
                            
                            # Notify the server
                            await ctx.send_msgs([
                                {"cmd": "LocationChecks", 
                                 "locations": [location_id]}
                            ])
                            
                except Exception as e:
                    logger.error(f"Error checking location {location_name}: {e}")
                    
            # Sleep for a short time to avoid excessive CPU usage
            await asyncio.sleep(0.5)
            
        except Exception as e:
            logger.error(f"Error in game sync task: {e}")
            await asyncio.sleep(1)  # Sleep longer on error


if __name__ == '__main__':
    # Text Mode to use !hint and such with games that have no text entry
    Utils.init_logging("SettlersClient")

    options = Utils.get_options()
    DISPLAY_MSGS = options.get("settlers_options", {}).get("display_msgs", True)

    async def main(args):
        ctx = SettlersContext(args.connect, args.password)
        ctx.server_task = asyncio.create_task(server_loop(ctx), name="ServerLoop")
        if gui_enabled:
            ctx.run_gui()
        ctx.run_cli()
        
        # Start the game sync task
        ctx.game_sync_task = asyncio.create_task(game_sync_task(ctx), name="Game Sync")

        await ctx.exit_event.wait()
        ctx.server_address = None

        await ctx.shutdown()

        if ctx.game_sync_task:
            await ctx.game_sync_task


    import colorama

    parser = get_base_parser()
    parser.add_argument('--url', default=None, help='Archipelago URL to connect to.')
    args = parser.parse_args()
    
    if args.url:
        args = handle_url_arg(args, parser)
        
    colorama.just_fix_windows_console()

    asyncio.run(main(args))
    colorama.deinit()
