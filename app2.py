import streamlit as st

# Page title
st.title("My Basic Streamlit App")

# Subtitle / header
st.header("User Input Section")

# Text input
name = st.text_input("Enter your name:")

# Number input
age = st.number_input("Enter your age:", min_value=0, max_value=120, step=1)

# Dropdown / selectbox
choice = st.selectbox("Select an option:", ["Option A", "Option B", "Option C"])

# Button
if st.button("Submit"):
    st.success(f"Hello {name}! You selected {choice} and your age is {age}.")

# Display sidebar
st.sidebar.title("Sidebar")
st.sidebar.info("This is a simple sidebar.")

