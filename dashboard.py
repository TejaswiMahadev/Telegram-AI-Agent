
import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import plotly.express as px
import plotly.graph_objects as go
from pymongo import MongoClient
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Page configuration
st.set_page_config(
    page_title="Bot Analytics",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)
st.markdown("""
    <style>
        /* Main container */
        .main > div {
            padding: 2rem;
        }
        
        /* Section headers */
        .section-header {
            padding: 1rem 0;
            margin-bottom: 2rem;
            border-bottom: 2px solid #f0f2f6;
        }
        
        /* Cards */
        .metric-card {
            background-color: white;
            padding: 1.5rem;
            border-radius: 0.5rem;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }
        
        /* Charts */
        .chart-container {
            background-color: white;
            padding: 1rem;
            border-radius: 0.5rem;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
            margin: 1rem 0;
        }
        
        /* Hide Streamlit branding */
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        
        /* Improve spacing */
        .stPlotlyChart {
            margin: 1rem 0;
        }
    </style>
""", unsafe_allow_html=True)

@st.cache_resource
def init_db():
    client = MongoClient(os.getenv("MONGO_URI"))
    return client.telegram_bot

@st.cache_data(ttl=300)
def get_users_data():
    db = init_db()
    return list(db.users.find())

def main():
    st.sidebar.title("📊 Dashboard Controls")
    st.sidebar.markdown("### 📅 Time Range")
    end_date = datetime.now()
    start_date = end_date - timedelta(days=30)
    date_range = st.sidebar.date_input(
        "Select period",
        value=(start_date, end_date),
        max_value=end_date
    )
    st.sidebar.markdown("### 🎯 Activity Filter")
    activity_types = ["All", "Search", "Chat", "Files"]
    selected_activities = st.sidebar.multiselect(
        "Select activities",
        activity_types,
        default=["All"]
    )
    st.title("Bot Analytics Dashboard")
    users_data = get_users_data()
    st.markdown("### 📈 Key Metrics")
    col1, col2, col3, col4 = st.columns(4)
    
    total_users = len(users_data)
    total_searches = sum(len(user.get('searches', [])) for user in users_data)
    total_chats = sum(len(user.get('chat_history', [])) for user in users_data)
    total_files = sum(len(user.get('files', [])) for user in users_data)
    
    with col1:
        st.metric("Total Users", f"{total_users:,}", "+12%")
    with col2:
        st.metric("Total Searches", f"{total_searches:,}", "+8%")
    with col3:
        st.metric("Chat Messages", f"{total_chats:,}", "+15%")
    with col4:
        st.metric("Files Processed", f"{total_files:,}", "+5%")
    
    # Activity Analysis Section
    st.markdown("### 📊 Activity Analysis")
    
    activity_data = []
    for user in users_data:
  
        for search in user.get('searches', []):
            activity_data.append({
                'date': search['timestamp'],
                'type': 'Search',
                'user_id': user['chat_id']
            })

        for chat in user.get('chat_history', []):
            activity_data.append({
                'date': chat['timestamp'],
                'type': 'Chat',
                'user_id': user['chat_id']
            })
    
        for file in user.get('files', []):
            activity_data.append({
                'date': file['timestamp'],
                'type': 'File',
                'user_id': user['chat_id']
            })
    
    if activity_data:
  
        df = pd.DataFrame(activity_data)
        df['date'] = pd.to_datetime(df['date'])
        
     
        mask = (df['date'].dt.date >= date_range[0]) & (df['date'].dt.date <= date_range[1])
        filtered_df = df[mask]
        
  
        col1, col2 = st.columns(2)
        
        with col1:
      
            daily_activity = filtered_df.groupby([filtered_df['date'].dt.date, 'type']).size().reset_index(name='count')
            fig = px.line(daily_activity, 
                         x='date', 
                         y='count', 
                         color='type',
                         title='Daily Activity Trends',
                         template='plotly_white')
            fig.update_layout(
                height=400,
                margin=dict(l=20, r=20, t=40, b=20),
                legend_title_text='Activity Type',
                xaxis_title='Date',
                yaxis_title='Number of Activities'
            )
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
       
            activity_dist = filtered_df['type'].value_counts()
            fig = px.pie(values=activity_dist.values,
                        names=activity_dist.index,
                        title='Activity Distribution',
                        template='plotly_white',
                        hole=0.4)
            fig.update_layout(
                height=400,
                margin=dict(l=20, r=20, t=40, b=20),
                showlegend=True
            )
            st.plotly_chart(fig, use_container_width=True)
    
    # User Engagement Section
    st.markdown("### 👥 User Engagement")
    
 
    engagement_data = []
    for user in users_data:
        engagement_data.append({
            'user_id': user['chat_id'],
            'searches': len(user.get('searches', [])),
            'chats': len(user.get('chat_history', [])),
            'files': len(user.get('files', []))
        })
    
    if engagement_data:
        engagement_df = pd.DataFrame(engagement_data)
        fig = go.Figure()
        for col in ['searches', 'chats', 'files']:
            fig.add_trace(go.Box(y=engagement_df[col], name=col.capitalize()))
            
        fig.update_layout(
                title='User Engagement Distribution',
                template='plotly_white',
                height=400,
                margin=dict(l=20, r=20, t=40, b=20),
                showlegend=True
            )
        st.plotly_chart(fig, use_container_width=True)
if __name__ == "__main__":
    main()
