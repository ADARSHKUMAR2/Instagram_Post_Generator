import streamlit as st
import requests
import datetime

# Set page config
st.set_page_config(page_title="Insta-Post AI", page_icon="📸", layout="centered")

st.title("📸 AI Instagram Manager")
st.markdown("Generate data-grounded posts using live News & Weather MCPs.")

# URL of our Dockerized Brain API
API_URL = "http://brain:8000/api/generate-post"
PUBLISH_URL = "http://brain:8000/api/publish-post"
QUEUE_URL = "http://brain:8000/api/queue-post"
QUEUE_STATUS_URL = "http://brain:8000/api/queue-status"
DELETE_QUEUE_URL = "http://brain:8000/api/queue"
HISTORY_URL = "http://brain:8000/api/search-history"
DB_STATUS_URL = "http://brain:8000/api/db-status"

# Initialize Session State keys
if "generated_caption" not in st.session_state:
    st.session_state.generated_caption = None
if "generated_image_url" not in st.session_state:
    st.session_state.generated_image_url = None
if "image_prompt" not in st.session_state:
    st.session_state.image_prompt = None
if "drive_matches" not in st.session_state:
    st.session_state.drive_matches = []
# New memory cache for raw image bytes to prevent re-fetching on rerun
if "image_cache" not in st.session_state:
    st.session_state.image_cache = {}

# User Input
user_prompt = st.text_area(
    "What should we post about today?", 
    placeholder="e.g., Give me an update on the UEFA Champions league..."
)

# --- POST GENERATION TRIGGER ---
if st.button("Generate Post 🚀", type="primary"):
    if not user_prompt:
        st.warning("Please enter a prompt first!")
    else:
        with st.spinner("Agent is fetching live data and writing..."):
            try:
                response = requests.post(API_URL, json={"prompt": user_prompt})
                if response.status_code == 200:
                    data = response.json()
                    post_content = data.get("content", {})

                    # Clear previous cache on new generation
                    st.session_state.image_cache = {}

                    # Update session state values
                    st.session_state.generated_caption = post_content.get("caption", "No caption found.")
                    st.session_state.image_prompt = post_content.get("image_prompt", "No image prompt found.")
                    st.session_state.generated_image_url = data.get("image_url")
                    st.session_state.drive_matches = data.get("drive_matches", [])
                    
                    # Force a clean UI refresh to enter the rendering view
                    st.rerun()
                else:
                    st.error(f"Failed to generate post. Status Code: {response.status_code}")

            except requests.exceptions.ConnectionError:
                st.error("🚨 Could not connect to the Brain API. Is the Docker container running?")
            except Exception as e:
                st.error(f"🚨 An error occurred: {e}")

st.divider()
st.subheader("🎵 Soundtrack Your Post")
st.markdown("Find the perfect Apple Music track to accompany this visual.")

if st.button("Fetch Track Recommendations 🎧", use_container_width=True):
    search_seed = st.session_state.image_prompt if st.session_state.image_prompt else "trending hits"
    
    with st.spinner("Vibe-checking your prompt with the music database..."):
        try:
            spot_res = requests.post("http://brain:8000/api/music-recommendations", json={"prompt": search_seed})
            if spot_res.status_code == 200:
                data = spot_res.json()
                if data["status"] == "success":
                    st.session_state.spotify_tracks = data["tracks"]
                else:
                    st.warning(f"Music API Error: {data['message']}")
        except Exception as e:
            st.error("Could not reach the music integration.")
            
# Render the dynamic Music cards if they exist in memory
if "spotify_tracks" in st.session_state and st.session_state.spotify_tracks:
    spot_cols = st.columns(len(st.session_state.spotify_tracks))
    for idx, track in enumerate(st.session_state.spotify_tracks):
        with spot_cols[idx]:
            with st.container(border=True):
                if track["image"]:
                    st.image(track["image"], use_column_width=True)
                st.markdown(f"**{track['name']}**")
                st.caption(f"👤 {track['artist']}")
                st.markdown(f"[Listen on Apple Music]({track['url']})")

# --- PERSISTENT RENDERING & PUBLISHING VIEW ---
if st.session_state.generated_caption:
    
    st.subheader("📝 Instagram Caption")
    st.info(st.session_state.generated_caption)
    
    if st.session_state.image_prompt:
        st.caption(f"**AI Visual Context:** {st.session_state.image_prompt}")
    
    st.divider()
    st.subheader("🖼️ Image Gallery")
    st.markdown("Select the final asset to push to your Instagram feed.")
    
    ai_url = st.session_state.get("generated_image_url")
    drive_matches = st.session_state.get("drive_matches", [])
    
    # 1. Build the dynamic options list
    image_options = ["🤖 AI Generated"]
    for i in range(len(drive_matches)):
        image_options.append(f"📁 Drive Match {i+1}")
        
    # 2. The Selection Tool (Clean horizontal radio button on top)
    selected_option = st.radio(
        "Which image should we publish?", 
        image_options, 
        horizontal=True,
        label_visibility="collapsed"
    )
    
    st.write("") # Add breathing room
    
    # 3. Build a beautiful, responsive visual grid
    total_options = len(image_options)
    
    # Defensive Layout: Center and constrain single AI image if no drive matches exist
    if total_options == 1:
        cols = st.columns([1, 2, 1])
        target_col = cols[1]
    else:
        cols = st.columns(total_options)
        target_col = cols[0]
    
    # Render AI Image
    with target_col:
        is_selected = selected_option == "🤖 AI Generated"
        with st.container(border=is_selected): 
            st.markdown(f"**🤖 AI Concept** {'✅' if is_selected else ''}")
            if ai_url:
                # Only attempt to fetch if it hasn't been cached yet
                if "ai_image" not in st.session_state.image_cache:
                    try:
                        ai_res = requests.get(ai_url, timeout=15)
                        # CRITICAL FIX: Verify the response is an actual image asset, not a text error page!
                        if ai_res.status_code == 200 and "image" in ai_res.headers.get("Content-Type", "").lower():
                            st.session_state.image_cache["ai_image"] = ai_res.content
                    except:
                        pass
                
                # Render the image if valid bytes exist, otherwise show a clean fallback message
                if "ai_image" in st.session_state.image_cache:
                    st.image(st.session_state.image_cache["ai_image"], use_column_width=True)
                else:
                    st.write("")
                    st.warning("🤖 AI generation is temporarily congested. Try generating again, or publish using one of your excellent Drive matches!")
            else:
                st.warning("No AI URL provided.")
                
    # Render Drive Matches (Only runs if matches are found)
    if total_options > 1:
        for i, file_id in enumerate(drive_matches):
            option_name = f"📁 Drive Match {i+1}"
            with cols[i+1]:
                is_selected = selected_option == option_name
                with st.container(border=is_selected):
                    st.markdown(f"**{option_name}** {'✅' if is_selected else ''}")
                    
                    # Read from RAM if already downloaded, otherwise fetch once
                    cache_key = f"drive_{file_id}"
                    if cache_key not in st.session_state.image_cache:
                        secure_url = f"http://brain:8000/api/image/{file_id}"
                        try:
                            img_response = requests.get(secure_url, timeout=15)
                            if img_response.status_code == 200:
                                st.session_state.image_cache[cache_key] = img_response.content
                        except:
                            st.error("Container network error.")
                    
                    if cache_key in st.session_state.image_cache:
                        st.image(st.session_state.image_cache[cache_key], use_column_width=True)
                    else:
                        st.error("Image load failed.")
    
    st.divider()
    
    # THE PUBLISH ACTIONS
    if st.button("📲 Approve & Publish to Instagram", type="primary", use_container_width=True, key="publish_meta_btn"):
        
        is_drive = "Drive Match" in selected_option
        
        if is_drive:
            match_index = int(selected_option.split()[-1]) - 1
            final_image_target = drive_matches[match_index]
            publish_endpoint = "http://brain:8000/api/publish-from-drive"
            payload = {"drive_file_id": final_image_target, "caption": st.session_state.generated_caption}
        else:
            final_image_target = ai_url
            publish_endpoint = PUBLISH_URL
            payload = {"image_url": final_image_target, "caption": st.session_state.generated_caption}

        with st.spinner(f"Publishing {selected_option} directly to Meta pipelines..."):
            try:
                pub_req = requests.post(publish_endpoint, json=payload)
                
                if pub_req.status_code == 200:
                    st.success("🎉 Successfully published to your Instagram feed!")
                    st.balloons()
                    
                    # Clear state and cache after publish
                    for key in ['generated_caption', 'generated_image_url', 'image_prompt', 'drive_matches', 'image_cache']:
                        if key in st.session_state:
                            del st.session_state[key]
                    st.rerun()
                else:
                    st.error(f"Failed to publish: {pub_req.text}")
            except Exception as e:
                st.error(f"Transmission error: {e}")

st.divider()
st.subheader("📁 Publish from Google Drive")
st.markdown("Fetch an image securely from Drive and push it to Instagram.")

# 1. Standard Inputs
drive_url = st.text_input("Google Drive File Link (or ID):", placeholder="Paste the share link here...")
drive_caption = st.text_area("Caption for Drive Image:", placeholder="Write your Instagram caption here...")

# Extract ID logic
file_id = ""
if drive_url:
    file_id = drive_url
    if "id=" in drive_url:
        file_id = drive_url.split("id=")[1].split("&")[0]
    elif "/d/" in drive_url:
        file_id = drive_url.split("/d/")[1].split("/")[0]

# 2. The Publishing Tabs
tab1, tab2 = st.tabs(["🚀 Publish Immediately", "⏰ Schedule for Later"])

# --- TAB 1: Publish Now ---
with tab1:
    st.caption("This will bypass the database queue and push to Instagram right now.")
    if st.button("🚀 Publish Now", type="primary", use_container_width=True):
        if not file_id or not drive_caption:
            st.warning("Please provide both a Drive link and a caption.")
        else:
            with st.spinner("Pulling from Drive and pushing directly to Meta..."):
                try:
                    response = requests.post(
                        "http://brain:8000/api/publish-from-drive", 
                        json={
                            "drive_file_id": file_id,
                            "caption": drive_caption
                        }
                    )
                    
                    if response.status_code == 200:
                        st.success("🎉 Post published successfully!")
                        st.balloons()
                    else:
                        st.error(f"Failed to publish: {response.text}")
                        
                except Exception as e:
                    st.error(f"🚨 Connection error: {e}")

# --- TAB 2: Schedule (Queue) ---
with tab2:
    st.caption("Send this to the database. The background worker will publish it at the requested time.")
    col1, col2 = st.columns(2)
    with col1:
        target_date = st.date_input("Select Date")
    with col2:
        target_time = st.time_input("Select Time")

    if st.button("⏰ Add to Queue", type="primary", use_container_width=True):
        if not file_id or not drive_caption:
            st.warning("Please provide both a Drive link and a caption.")
        else:
            scheduled_datetime = datetime.datetime.combine(target_date, target_time)

            with st.spinner("Locking post into the database queue..."):
                try:
                    response = requests.post(
                        QUEUE_URL, 
                        json={
                            "source_type": "drive",
                            "file_id_or_url": file_id,
                            "caption": drive_caption,
                            "scheduled_time": scheduled_datetime.isoformat() 
                        }
                    )
                    
                    if response.status_code == 200:
                        data = response.json()
                        st.success(f"🎉 {data['message']}")
                        st.info(f"Worker will publish this on {scheduled_datetime.strftime('%b %d at %I:%M %p')}.")
                    else:
                        st.error(f"Failed to queue: {response.text}")
                        
                except Exception as e:
                    st.error(f"🚨 Connection error: {e}")

st.divider()
st.subheader("🛠️ System Administration Dashboard")
st.markdown("Monitor background workers, search logs, and database health.")

dash_tab1, dash_tab2, dash_tab3 = st.tabs(["📊 Background Queue", "🕰️ Search History", "🧠 ChromaDB Diagnostics"])

# --- DASHBOARD TAB 1: QUEUE ---
with dash_tab1:
    col1, col2 = st.columns([4, 1])
    with col2:
        if st.button("🔄 Refresh Queue", use_container_width=True):
            st.rerun()

    try:
        response = requests.get(QUEUE_STATUS_URL)
        if response.status_code == 200:
            queue_data = response.json().get("queue", [])
            
            if not queue_data:
                st.info("The queue is currently empty.")
            else:
                for post in queue_data:
                    status_color = "gray"
                    if post['status'] == 'pending': status_color = "orange"
                    if post['status'] == 'processing': status_color = "blue"
                    if post['status'] == 'completed': status_color = "green"
                    if post['status'] == 'failed': status_color = "red"
                    
                    with st.container(border=True):
                        st.markdown(f"**🗓️ Scheduled:** {post['scheduled_time']} | **Status:** :{status_color}[{post['status'].upper()}]")
                        st.caption(f"**Source:** {post['source_type'].title()} | **ID/URL:** {post['file_id_or_url'][:30]}...")
                        st.write(f"💬 {post['caption']}")
                        
                        if post['status'] == 'pending':
                            if st.button(f"❌ Cancel Post #{post['id']}", key=f"cancel_{post['id']}", use_container_width=True):
                                del_res = requests.delete(f"{DELETE_QUEUE_URL}/{post['id']}")
                                if del_res.status_code == 200:
                                    st.success("Post removed from queue!")
                                    st.rerun()
        else:
            st.error("Could not fetch queue status.")
    except Exception as e:
        st.error(f"Could not connect to the queue database: {e}")

# --- DASHBOARD TAB 2: SEARCH HISTORY ---
with dash_tab2:
    st.caption("A chronological log of all semantic queries sent to your Google Drive vector database.")
    
    col1, col2 = st.columns([4, 1])
    with col2:
        if st.button("🔄 Refresh History", use_container_width=True):
            st.rerun()
            
    try:
        hist_res = requests.get(HISTORY_URL)
        if hist_res.status_code == 200:
            history_data = hist_res.json().get("history", [])
            
            if not history_data:
                st.info("No searches have been made yet.")
            else:
                for item in history_data:
                    with st.container(border=True):
                        st.caption(f"🕒 {item['timestamp']} (UTC)")
                        st.write(f"🔍 **Query:** {item['query']}")
        else:
            st.error("Failed to load history.")
    except Exception as e:
        st.error(f"Connection error: {e}")

# --- DASHBOARD TAB 3: DIAGNOSTICS ---
with dash_tab3:
    st.caption("Direct line to ChromaDB to verify ingested images and metadata.")
    
    if st.button("🔍 Run Database Check", use_container_width=True):
        with st.spinner("Peeking into the vector database..."):
            try:
                res = requests.get(DB_STATUS_URL)
                if res.status_code == 200:
                    data = res.json()
                    
                    if "error" in data:
                        st.error(f"Database Error: {data['error']}")
                    else:
                        st.metric(label="Total Vectors Indexed", value=data["count"])
                        
                        if data["count"] > 0:
                            st.success("Database is populated and healthy!")
                            st.write("**Recent Drive Ingestions:**")
                            st.json(data["recent"])
                        else:
                            st.warning("Database is currently empty.")
                else:
                    st.error("Failed to reach the diagnostic endpoint.")
            except Exception as e:
                st.error(f"🚨 Connection error: {e}")