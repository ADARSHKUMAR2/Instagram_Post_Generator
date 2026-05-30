import streamlit as st
import requests

# Set page config
st.set_page_config(page_title="Insta-Post AI", page_icon="📸", layout="centered")

st.title("📸 AI Instagram Manager")
st.markdown("Generate data-grounded posts using live News & Weather MCPs.")

# URL of our Dockerized Brain API
API_URL = "http://brain:8000/api/generate-post"
PUBLISH_URL = "http://brain:8000/api/publish-post"

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