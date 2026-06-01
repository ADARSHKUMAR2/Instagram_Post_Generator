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
QUEUE_URL="http://brain:8000/api/queue-post"
QUEUE_STATUS_URL="http://brain:8000/api/queue-status"
DELETE_QUEUE_URL="http://brain:8000/api/queue"

# Initialize Session State keys
if "generated_caption" not in st.session_state:
    st.session_state.generated_caption = None
if "generated_image_url" not in st.session_state:
    st.session_state.generated_image_url = None
if "image_prompt" not in st.session_state:
    st.session_state.image_prompt = None

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

                    # Update session state values
                    st.session_state.generated_caption = post_content.get("caption", "No caption found.")
                    st.session_state.image_prompt = post_content.get("image_prompt", "No image prompt found.")
                    st.session_state.generated_image_url = data.get("image_url")
                    
                    # Force a clean UI refresh to enter the rendering view
                    st.rerun()
                else:
                    st.error(f"Failed to generate post. Status Code: {response.status_code}")

            except requests.exceptions.ConnectionError:
                st.error("🚨 Could not connect to the Brain API. Is the Docker container running?")
            except Exception as e:
                st.error(f"🚨 An error occurred: {e}")

st.divider()

# --- PERSISTENT RENDERING & PUBLISHING VIEW ---
if st.session_state.generated_caption and st.session_state.generated_image_url:
    
    st.subheader("📝 Instagram Caption")
    st.info(st.session_state.generated_caption)
    
    st.subheader("🎨 Generated Layout")
    with st.spinner("🎨 Visualizing post layout..."):
        try:
            # Fetch layout bytes to handle external image rendering safely
            img_response = requests.get(st.session_state.generated_image_url, timeout=30)
            if img_response.status_code == 200:
                st.image(img_response.content, use_column_width=True)
            else:
                st.image(st.session_state.generated_image_url, use_column_width=True)
        except Exception as img_err:
            st.error(f"Could not render image preview: {img_err}")
            st.markdown(f"**[🔗 Open Image Link Directly]({st.session_state.generated_image_url})**")
    
    if st.session_state.image_prompt:
        st.subheader("⚙️ Visual Generation Context")
        st.caption(st.session_state.image_prompt)
    
    st.divider()
    
    # THE PUBLISH ACTIONS
    if st.button("📲 Approve & Publish to Instagram", type="primary", use_container_width=True):
        with st.spinner("Publishing container layout directly to Meta pipelines..."):
            try:
                pub_req = requests.post(
                    PUBLISH_URL, 
                    json={
                        "image_url": st.session_state.generated_image_url, 
                        "caption": st.session_state.generated_caption
                    }
                )
                
                if pub_req.status_code == 200:
                    st.success("🎉 Successfully published to your Instagram feed!")
                    st.balloons()
                    
                    # Clear state after successful publication
                    st.session_state.generated_caption = None
                    st.session_state.generated_image_url = None
                    st.session_state.image_prompt = None
                else:
                    st.error(f"Failed to publish: {pub_req.text}")
            except Exception as e:
                st.error(f"Transmission error: {e}")

st.divider()
st.subheader("📁 Publish from Google Drive")
st.markdown("Fetch an image securely from Drive and push it to Instagram.")

# 1. Standard Inputs (Shared across both tabs)
drive_url = st.text_input("Google Drive File Link (or ID):", placeholder="Paste the share link here...")
drive_caption = st.text_area("Caption for Drive Image:", placeholder="Write your Instagram caption here...")

# Extract ID logic so both buttons can use it
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
                    # Hits your immediate publishing endpoint
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
                    # Hits your queue endpoint
                    response = requests.post(
                        "http://brain:8000/api/queue-post", 
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
st.subheader("📊 Background Queue Dashboard")

# Add a refresh button
col1, col2 = st.columns([4, 1])
with col2:
    if st.button("🔄 Refresh Queue"):
        st.rerun()

try:
    response = requests.get(QUEUE_STATUS_URL)
    if response.status_code == 200:
        queue_data = response.json().get("queue", [])
        
        if not queue_data:
            st.info("The queue is currently empty.")
        else:
            # Display each post in a clean card format
            for post in queue_data:
                # Color code the status
                status_color = "gray"
                if post['status'] == 'pending': status_color = "orange"
                if post['status'] == 'processing': status_color = "blue"
                if post['status'] == 'completed': status_color = "green"
                if post['status'] == 'failed': status_color = "red"
                
                with st.container(border=True):
                    st.markdown(f"**🗓️ Scheduled:** {post['scheduled_time']} | **Status:** :{status_color}[{post['status'].upper()}]")
                    st.caption(f"**Source:** {post['source_type'].title()} | **ID/URL:** {post['file_id_or_url'][:30]}...")
                    st.write(f"💬 {post['caption']}")
                    
                    # Add a cancel button for pending posts
                    if post['status'] == 'pending':
                        if st.button(f"❌ Cancel Post #{post['id']}", key=f"cancel_{post['id']}"):
                            del_res = requests.delete(f"{DELETE_QUEUE_URL}/{post['id']}")
                            if del_res.status_code == 200:
                                st.success("Post removed from queue!")
                                st.rerun()
                                
    else:
        st.error("Could not fetch queue status.")
except Exception as e:
    st.error(f"Could not connect to the queue database: {e}")