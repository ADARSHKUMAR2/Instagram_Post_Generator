import streamlit as st
import requests
import json

# Set page config
st.set_page_config(page_title="Insta-Post AI", page_icon="📸", layout="centered")

st.title("📸 AI Instagram Manager")
st.markdown("Generate data-grounded posts using live News & Weather MCPs.")

# URL of our Dockerized Brain API
API_URL = "http://brain:8000/api/generate-post"

# User Input
user_prompt = st.text_area("What should we post about today?", placeholder="e.g., Give me an update on the UEFA Champions league...")

if st.button("Generate Post 🚀", type="primary"):
    if not user_prompt:
        st.warning("Please enter a prompt first!")
    else:
        with st.spinner("Agent is fetching live data and writing..."):
            try:
                # Send the prompt to the backend
                response = requests.post(API_URL, json={"prompt": user_prompt})
                if response.status_code == 200:
                    st.success("Post generated successfully!")
                    
                    # 1. Parse the JSON response
                    data = response.json()
                    
                    # 2. Extract the nested 'content' dictionary (your InstaPost object)
                    post_content = data.get("content", {})
                    
                    # 3. Pull the caption and image prompt from inside 'post_content'
                    caption = post_content.get("caption", "No caption found.")
                    image_prompt = post_content.get("image_prompt", "No image prompt found.")

                    image_url = data.get("image_url") # <--- GET THE URL

                    # --- Display the Results ---
                    st.subheader("📝 Instagram Caption")
                    st.info(caption)
                    
                    st.subheader("🎨 Generated Image")
                    if image_url:
                        # 1. Create a mini spinner specifically for the image generation
                        with st.spinner("🎨 Visualizing post layout..."):
                            try:
                                # Fetch the actual image bytes directly from Pollinations
                                # This blocks for 2-3 seconds until the image is fully generated
                                img_response = requests.get(image_url, timeout=30)
                                
                                if img_response.status_code == 200:
                                    # Pass the raw image bytes straight to st.image
                                    st.image(img_response.content, use_column_width=True)
                                else:
                                    st.warning("Image generation timed out on the server side. Try the link below!")
                            except Exception as img_err:
                                st.error(f"Could not render image layout: {img_err}")
                        
                        # Keep the fallback link just in case
                        st.markdown(f"**[🔗 Open High-Res Image in New Tab]({image_url})**")
                    else:
                        st.warning("No image URL received from the backend.")
                            
                    st.subheader("⚙️ DALL-E Prompt Used")
                    st.caption(image_prompt)

                else:
                    st.error(f"Failed to generate post. Status Code: {response.status_code}")

            except requests.exceptions.ConnectionError:
                st.error("🚨 Could not connect to the Brain API. Is the Docker container running?")
            except Exception as e:
                st.error(f"🚨 An error occurred: {e}")