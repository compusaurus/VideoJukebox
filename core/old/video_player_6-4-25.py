# core/video_player.py
import os
import vlc
import platform
import logging

logger = logging.getLogger("VideoJukebox.VideoPlayer")

class VideoPlayer:
    def __init__(self, settings_manager, on_media_list_player_event=None):
        self.settings_manager = settings_manager
        self.on_media_list_player_event = on_media_list_player_event

        logger.info("Initializing VideoPlayer with MediaListPlayer approach.")
        
        # 1. Create VLC Instance
        # ENABLE VERBOSE VLC LOGGING TO A FILE
        vlc_args = [
            "--no-qt-privacy-ask", # Prevent potential Qt dialogs
            "--no-metadata-network-access", # Don't fetch metadata online
            "--no-stats", # Disable statistics
            # "--aout=waveout", # TRY FORCING A DIFFERENT AUDIO OUTPUT MODULE on Windows (e.g., waveout, directsound)
                              # Other options: "directsound", "amem" (no audio, for testing)
            "--no-video-title-show", # Don't show title on video
            # "--vout=dummy", # EXTREME: Disable video output entirely for testing if audio is the problem
            # "--verbose=0", # Reduce verbosity for now unless debugging log file writing
        ]
        # Forcing log file again, try a very simple path first
        log_file_path = "vlc_native_from_class.txt" 
        vlc_args.extend([
            "--verbose=2", 
            f"--logfile={log_file_path}", # Log to current working directory
            "--logmode=text",
            "--file-logging" 
        ])
        # You can also try adding:
        # "--no-qt-privacy-ask --no-metadata-network-access" 
        # to prevent any potential startup dialogs from VLC itself if run in a weird context.
        try:
            logger.info(f"Attempting vlc.Instance with args: {vlc_args}")
            self.instance = vlc.Instance(vlc_args)
            logger.info(f"VLC Instance CREATED: {self.instance}")
            import time
            time.sleep(0.2) # Wait 200ms
            logger.info("Short delay after VLC Instance creation.")            
        except Exception as e:
            logger.error(f"Failed to create VLC instance with args {vlc_args}: {e}", exc_info=True)
            raise RuntimeError(f"Could not initialize VLC Instance for VideoPlayer. Args: {vlc_args}") from e
        #
        # 2. Create MediaList
        logger.debug("Attempting self.instance.media_list_new()...")
        self.media_list = self.instance.media_list_new()
        # Your debug prints for success/failure of media_list_new from the example
        # are good here. Let's integrate them with logging.
        if self.media_list is None:
            logger.error("self.instance.media_list_new() FAILED (returned None).")
            print("\nERROR: media_list_new() returned None.") # Console for immediate visibility
            print("  → That means libVLC could not load the 'playlist' plugin.")
            print("  → Double‐check that VLC_PLUGIN_PATH and PATH point to the correct folders.")
            if self.instance: self.instance.release()
            # sys.exit(1) might be too harsh here if this class is part of a larger app.
            # Let the RuntimeError propagate.
            raise RuntimeError("Could not create VLC MediaList.")
        else:
            logger.info(f"VLC MediaList CREATED: {self.media_list}")
            print(f">>> [Debug] instance.media_list_new() → {self.media_list}") # Mimic example
            print("    🎉 media_list_new() succeeded!")


        # 3. Create MediaListPlayer
        logger.debug("Attempting self.instance.media_list_player_new()...")
        self.ml_player = self.instance.media_list_player_new()
        if not self.ml_player:
            logger.error("Failed to create VLC MediaListPlayer.")
            if self.instance: self.instance.release()
            if self.media_list: self.media_list.release()
            raise RuntimeError("Could not create VLC MediaListPlayer.")
        logger.info(f"VLC MediaListPlayer CREATED: {self.ml_player}")
        
        # 4. Set MediaList for the MediaListPlayer
        logger.debug(f"Setting media_list {self.media_list} for ml_player {self.ml_player}")
        self.ml_player.set_media_list(self.media_list)
        logger.debug("MediaList successfully set for MediaListPlayer.")
        logger.info(f"VLC MediaList CREATED: {self.media_list}") # This should still log as an object
        
        # 5. Get the underlying MediaPlayer
        logger.debug(f"Getting underlying MediaPlayer from ml_player {self.ml_player}...")
        self.media_player = self.ml_player.get_media_player() 
        if not self.media_player:
            logger.error("Failed to get MediaPlayer from MediaListPlayer.")
            if self.instance: self.instance.release()
            if self.media_list: self.media_list.release()
            if self.ml_player: self.ml_player.release()
            raise RuntimeError("Could not get MediaPlayer from MediaListPlayer.")
        logger.info(f"Underlying MediaPlayer obtained: {self.media_player}")

        # Initialize other attributes
        self.embedded_frame_widget_id = None
        self.current_song_info = None 

        # 6. Set up event managers
        logger.debug("Setting up event managers...")
        mlp_events = self.ml_player.event_manager()
        if mlp_events:
            mlp_events.event_attach(vlc.EventType.MediaListPlayerNextItemSet, self._handle_next_item_set)
            logger.debug("Attached MediaListPlayerNextItemSet event.")
        else:
            logger.warning("Could not get event manager for MediaListPlayer.")

        player_events = self.media_player.event_manager()
        if player_events:
            player_events.event_attach(vlc.EventType.MediaPlayerEndReached, self._handle_single_media_ended)
            player_events.event_attach(vlc.EventType.MediaPlayerEncounteredError, self._handle_media_error)
            logger.debug("Attached MediaPlayerEndReached and MediaPlayerEncounteredError events.")
        else:
            logger.warning("Could not get event manager for underlying MediaPlayer.")

        logger.info("VideoPlayer initialization complete.")

    def _handle_next_item_set(self, event):
        # event.u.media_list_player_next_item_set.item is the new vlc.Media object
        new_media = event.u.media_list_player_next_item_set.item
        if new_media:
            mrl = new_media.get_mrl()
            logger.info(f"MediaListPlayer Event: NextItemSet. New MRL: {mrl}")
        # We need to map this MRL back to our song_info if we want to update UI
        # This requires VideoPlayer to know about the songs it was given.
        # For now, the main app will need to manage this if detailed info is needed.
        # We can pass the MRL to the main app's callback.
        if self.on_media_list_player_event:
            self.on_media_list_player_event(event_type="NextItemSet", mrl=mrl)
        else:
            logger.info("MediaListPlayer Event: NextItemSet, but no new item (likely end of list or error).")
            """ 
            This fires whenever VLC’s MediaListPlayer is about to start the next media item.
            We must guard against the union not having a .media_list_player_next_item_set member,
            or else we get ‘AttributeError: EventUnion has no attribute media_list_player_next_item_set.’
            """
            if not hasattr(event.u, "media_list_player_next_item_set"):
                logger.warning("Got NextItemSet event, but union has no media_list_player_next_item_set. Skipping.")
                return
            new_media = event.u.media_list_player_next_item_set.item
            if new_media:
                logger.info(f"MediaListPlayer Event: NextItemSet. New MRL: {mrl}")
                if self.on_media_list_player_event:
                # Notify the main UI that “track with this MRL is now playing”
                    self.on_media_list_player_event(event_type="NextItemSet", mrl=mrl)
                else:
                    logger.info("MediaListPlayer Event: NextItemSet, but no new item (possibly end or error).")

    def _handle_single_media_ended(self, event):
        """
        This callback is invoked by VLC whenever the *current* MediaPlayer item finishes.
        At that point we want to:
          1) Log that it ended,
          2) Immediately remove index 0 from our MediaList (so it doesn’t stick around),
          3) Fire our own callback (so MainUI/QueueManager can update their “now playing” or “up‐next” lists).
        """
        logger.info("MediaPlayer Event: MediaPlayerEndReached for current item.")
        # ── Step 1: Remove the just‐played item from VLC’s media_list at index 0 ──
        try:
            if self.media_list is not None and self.media_list.count() > 0:
                self.media_list.remove_index(0)
                logger.debug("Removed index 0 from VLC MediaList so it won’t replay.")
        except Exception as e:
            logger.error(f"Error while removing finished item from MediaList: {e}", exc_info=True)

        # ── Step 2: Fire our “SingleMediaEnded” event back to the main app/QueueManager UI ──
        if self.on_media_list_player_event:
            # We could pass the MRL of the song that just ended here if you want.
            self.on_media_list_player_event(event_type="SingleMediaEnded")

    def _handle_media_error(self, event):
        logger.error("MediaPlayer Event: MediaPlayerEncounteredError.")
        if self.on_media_list_player_event:
            self.on_media_list_player_event(event_type="MediaError")

    def set_embedding_widget(self, frame_widget):
        """Call this once from PlayerUI to set the target frame."""
        if frame_widget:
            self.embedded_frame_widget_id = frame_widget.winfo_id()
            logger.info(f"Embedding frame ID set: {self.embedded_frame_widget_id}")
            # Embed immediately if player exists
            if self.media_player and self.embedded_frame_widget_id:
                self._embed_player()
        else:
            logger.error("set_embedding_widget called with None frame_widget.")

    def _embed_player(self):
        """Internal method to perform embedding using the stored ID."""
        if self.media_player and self.embedded_frame_widget_id:
            logger.debug(f"Attempting to embed MediaPlayer {self.media_player} into frame ID: {self.embedded_frame_widget_id}")
            try:
                if platform.system() == "Linux":
                    self.media_player.set_xwindow(self.embedded_frame_widget_id)
                elif platform.system() == "Windows":
                    self.media_player.set_hwnd(self.embedded_frame_widget_id)
                elif platform.system() == "Darwin":
                    self.media_player.set_hwnd(self.embedded_frame_widget_id)
                logger.info(f"MediaPlayer embedding setup for frame ID: {self.embedded_frame_widget_id}")
            except Exception as e:
                logger.error(f"Error during MediaPlayer embedding: {e}", exc_info=True)
        # ... (warnings if player or ID is missing)

    def add_to_playlist(self, video_path, song_info):
        logger.info(f"ADD_TO_PLAYLIST CALLED FOR: {video_path}")

        # 1) Check for real VLC objects; only treat “None” as fatal
        if self.instance is None:
            logger.error("ADD_TO_PLAYLIST: CRITICAL FAILURE - self.instance IS NONE. Cannot add.")
            return False

        if self.ml_player is None:
            logger.error("ADD_TO_PLAYLIST: CRITICAL FAILURE - self.ml_player IS NONE. Cannot add.")
            return False

        if self.media_list is None:
            logger.error("ADD_TO_PLAYLIST: CRITICAL FAILURE - self.media_list IS NONE. Cannot add.")
            return False

        # (DO NOT do `if not self.media_list:` here. That rejects an empty MediaList.)

        # 2) Now build a VLC media object
        try:
            media = self.instance.media_new(video_path)
            if not media:
                logger.error(f"Failed to create VLC media object for: {video_path}")
                return False

            media.set_meta(vlc.Meta.NowPlaying,
                           f"{song_info.get('artist','')} - {song_info.get('title','')}")
            
            result_add = self.media_list.add_media(media)
            media.release()

            if result_add == 0:
                count = self.media_list.count()
                logger.info(f"Successfully added '{video_path}' to playlist. Count is now: {count}")
                return True
            else:
                logger.error(f"self.media_list.add_media() returned {result_add} for '{video_path}'")
                return False

        except Exception as e:
            logger.error(f"Exception while adding to playlist: {e}", exc_info=True)
            return False

    def play_playlist(self):
        if self.ml_player and self.media_list.count() > 0:
            logger.info("Starting/Resuming playlist playback.")
            self.ml_player.play()
            # Current song info update will happen via NextItemSet event
            return True
        elif not self.media_list.count() > 0:
            logger.info("Playlist is empty. Nothing to play.")
            return False
        else:
            logger.error("MediaListPlayer not initialized. Cannot play.")
            return False

    def stop(self):
        if self.ml_player:
            logger.info("Stopping MediaListPlayer.")
            self.ml_player.stop()
        self.current_song_info = None # Clear our tracked info

    def pause(self): # MediaListPlayer has pause/set_pause
        if self.ml_player:
            self.ml_player.pause() # Toggles pause

    def set_volume(self, volume): # Volume is on the underlying MediaPlayer
        if self.media_player:
            self.media_player.audio_set_volume(int(volume))

    def get_volume(self):
        return self.media_player.audio_get_volume() if self.media_player else 0

    def get_playlist_count(self): # Helper method you might need (from main.py refactor)
        return self.media_list.count() if self.media_list else 0

    def get_player_state(self): # This was the name in my previous refactor suggestion
        """Returns the current state of the MediaListPlayer.
           Consider renaming to get_state() for consistency if other parts of app use that,
           or update other parts to call get_player_state().
        """
        return self.ml_player.get_state() if self.ml_player else vlc.State.Ended

    def get_state(self): # State of the MediaListPlayer
        """Returns the current state of the MediaListPlayer."""
        if self.ml_player:
            return self.ml_player.get_state()
        return vlc.State.Ended # Default to Ended if ml_player is not initialized

    def get_current_song_info_from_player(self):
        # This attempts to get info from the currently playing item in the MediaPlayer
        # It requires the main app to map MRLs to full song_info if needed.
        if self.media_player:
            current_media = self.media_player.get_media()
            if current_media:
                mrl = current_media.get_mrl()
                # meta_title = current_media.get_meta(vlc.Meta.Title)
                # meta_artist = current_media.get_meta(vlc.Meta.Artist)
                # now_playing_meta = current_media.get_meta(vlc.Meta.NowPlaying) # What we set
                # logger.debug(f"Current media MRL: {mrl}, Title: {meta_title}, Artist: {meta_artist}, NowPlaying: {now_playing_meta}")
                current_media.release()
                return {"mrl": mrl} # Return MRL for mapping
        return None

    def release(self):
        
        logger.warning("== VIDEO_PLAYER.RELEASE() CALLED ==") # MAKE THIS STAND OUT
        
        logger.info("VideoPlayer (MediaList approach) release called.")
        if self.ml_player:
            self.ml_player.stop()
            self.ml_player.release()
            self.ml_player = None
        if self.media_player: # Though ml_player.release() should handle this
             # Detach events explicitly from the media_player before it's gone
            try:
                player_events = self.media_player.event_manager()
                if player_events:
                    player_events.event_detach(vlc.EventType.MediaPlayerEndReached)
                    player_events.event_detach(vlc.EventType.MediaPlayerEncounteredError)
            except Exception: pass # Ignore if already released
            self.media_player.release() # Should be released by ml_player, but for safety
            self.media_player = None
        if self.media_list:
            self.media_list.release()
            self.media_list = None
        if self.instance:
            self.instance.release()
            self.instance = None
        logger.info("VideoPlayer resources effectively released.") # Changed from "VideoPlayer resources released."