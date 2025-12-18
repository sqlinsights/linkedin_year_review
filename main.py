import streamlit as st
import pandas as pd
from typing import Optional, Union, List
from datetime import date
import pyautogui
import time
from jinja2 import Environment, FileSystemLoader
from html2image import Html2Image
from io import BytesIO
from PIL import Image
import humanize
import tempfile
temp_dir = tempfile.gettempdir()
# st.html('styles.css')

from pydantic import BaseModel

class Metric(BaseModel):
    label:str = ""
    value:Union[str,float, int] = None
    sub_label:Optional[str] = None
    type:str = "standard"
    pills:List = []
    span_class:str = "span-1"
class Chart(BaseModel):
    title:str
    type:str
    span_class:str
    height:int
    labels:List
    values:List

class LinkedInAnalyticsProcessor:
    def __init__(self):
        self.file = st.file_uploader("Drag/Drops your LinkedIn Analytics here")
        self.tabs = ['DISCOVERY', 'ENGAGEMENT','TOP POSTS', 'FOLLOWERS', 'DEMOGRAPHICS']
        self.data = {}
        if self.file:
            for tab in self.tabs:
                try:
                    self.data[tab] = pd.read_excel(self.file, sheet_name=tab)
                except Exception as e:
                    st.error("Unable to load analytics file")

        self.metrics = []
        self.charts = []
        self.metrics.append(Metric(label="", 
                                    value="LinkedIn Year in Review 2025",
                                    span_class="span-4"
                                    ).model_dump())         
    def process_engagement(self):
        engagement = self.data.get("ENGAGEMENT")
        engagement['Date'] = pd.to_datetime(engagement['Date'])
        engagement = engagement.loc[engagement['Date'].dt.year == 2025]
        most_impressions = engagement.sort_values(by='Impressions', ascending=False).head(1)
        most_engagements = engagement.sort_values(by='Engagements', ascending=False).head(1)
        self.metrics.append(Metric(label="Highest Reach Day", 
                                    value=humanize.intcomma(most_impressions['Impressions'].values[0]),
                                    sub_label=str(most_impressions['Date'].dt.date.values[0]),
                                    ).model_dump())
        self.metrics.append(Metric(label="Highest Engagement Day", 
                                    value=humanize.intcomma(most_engagements['Engagements'].values[0]),
                                    sub_label=str(most_engagements['Date'].dt.date.values[0])).model_dump())

    def process_posts(self):
        top_posts = self.data.get("TOP POSTS").iloc[1:]
        top_posts_eng = top_posts.iloc[:,:3]
        header = top_posts_eng.iloc[0]
        top_posts_eng = top_posts_eng[1:]
        top_posts_eng.columns = header

        top_posts_reach= top_posts.iloc[:, 4:7]
        header = top_posts_reach.iloc[0]
        top_posts_reach = top_posts_reach[1:]
        top_posts_reach.columns = header

        median_engagement= top_posts_eng['Engagements'].mean()
        median_reach = top_posts_reach['Impressions'].mean()
        top_post = top_posts_reach['Impressions'].values[0]
        self.metrics.append(Metric(label="Mean Reach", 
                                    value=humanize.intcomma(median_reach),
                                    ).model_dump())
        self.metrics.append(Metric(label="Mean Engagement", 
                                    value=humanize.intcomma(median_engagement),
                                    ).model_dump())
        self.metrics.append(Metric(label="Top Post Reach", 
                                    value=humanize.intcomma(top_post),
                                    ).model_dump())

    def process_followers(self):
        followers = self.data.get("FOLLOWERS").iloc[1:]
        header = followers.iloc[0]
        followers = followers[1:]
        followers.columns = header
        followers['Date'] = pd.to_datetime(followers['Date'])
        followers = followers.loc[followers['Date'].dt.year == 2025]
        followers['month'] = followers['Date'].dt.month_name()
        followers['month_number'] = followers['Date'].dt.month
        average_followers_per_month = followers.groupby(['month', 'month_number']).agg({"New followers":"sum"}).reset_index()
        average_followers_per_month = average_followers_per_month.sort_values(by='month_number')

        self.metrics.append(Metric(label="Average New Monthly Followers", 
                                    value=humanize.intcomma(int(round(average_followers_per_month['New followers'].mean(),0)))
                                    ).model_dump())
        self.charts.append(Chart(title="Average New Monthly Followers",
                                 type="line",
                                 span_class="span-4",
                                 height=150,
                                 labels=average_followers_per_month['month'],
                                 values=average_followers_per_month['New followers']
                                 ).model_dump())
        self.metrics.append(Metric(label="Total New Followers", 
                                    value=humanize.intcomma(int(round(average_followers_per_month['New followers'].sum(),0))), span_class="span-2"
                                    ).model_dump())

                
    def process_demographics(self):
        demographics = self.data.get("DEMOGRAPHICS").iloc[1:]
        for category in demographics['Top Demographics'].unique():
            if category in ['Job titles','Locations','Industries','Companies' ]:
                self.metrics.append(Metric(label=f"Engagement top {category}", 
                                        type="pill_list",
                                        pills = [i for i  in demographics.loc[demographics['Top Demographics'] == category]['Value']]
                                        ).model_dump())
            
            
# with st.container(key="instructions", border=True):            
st.subheader("Step 1", anchor=False)
st.link_button("Open your Dashboard", 
            url="https://www.linkedin.com/analytics/creator/content/?metricType=ENGAGEMENTS&timeRange=past_365_days",
            type="secondary",
            icon=":material/arrow_outward:",
            use_container_width=True)
st.subheader("Step 2", anchor=False)
st.write("Click on **:blue-background[:material/download: Export]**")
st.subheader("Step 3", anchor=False)
stats = LinkedInAnalyticsProcessor()
if stats.file:
    stats.process_engagement()
    stats.process_posts()
    stats.process_followers()
    stats.process_demographics()
    if st.button("Generate"):
        h2i = Html2Image(keep_temp_files=False, output_path=temp_dir)
        dashboard_data = {
            "metrics": stats.metrics,
            "charts": stats.charts
        }

        buffer = BytesIO()
        env = Environment(loader=FileSystemLoader('.'))
        template = env.get_template('template.html')
        html_content = template.render(dashboard_data)

        test = h2i.screenshot(
            html_str=html_content, 
            save_as='LinkedInYearReview.png',
            size=(1200,900)
        )
        with open(test[0], 'rb') as temp_created:
            st.download_button("Download Review", data=temp_created.read(), file_name="LinkedIn_Year_in_Review_2025.png" )
        h2i._remove_temp_file(test[0])
        st.info("Dashboard image generated successfully!")