import streamlit as st
import pandas as pd
import plotly.express as px
from github import Github
from datetime import datetime, timedelta
import re

# Data Collection Module
def collect_github_data(repo_url):
    # Extract owner and repo name from the URL
    match = re.match(r"https://github.com/([^/]+)/([^/]+)", repo_url)
    if not match:
        st.error("Invalid GitHub repository URL")
        return None

    owner, repo_name = match.groups()

    # Initialize PyGithub
    try:
        g = Github(st.secrets["github_token"])
        repo = g.get_repo(f"{owner}/{repo_name}")
    except Exception as e:
        st.error(f"Error accessing GitHub: {e}")
        return None  # Return None if there's an error

    # Collect data for the last 30 days
    end_date = datetime.now()
    start_date = end_date - timedelta(days=30)

    # Collect commits
    commits = list(repo.get_commits(since=start_date, until=end_date))

    # Collect pull requests
    pull_requests = list(repo.get_pulls(state='all', sort='created', base='main'))
    pull_requests = [pr for pr in pull_requests if start_date <= pr.created_at <= end_date]

    # Collect issues
    issues = list(repo.get_issues(state='all', since=start_date))

    # Collect code reviews (comments on pull requests)
    code_reviews = []
    for pr in pull_requests:
        reviews = list(pr.get_reviews())
        code_reviews.extend(reviews)

    # Collect new contributors
    contributors = {commit.author.login for commit in commits}

    return {
        'commits': commits,
        'pull_requests': pull_requests,
        'issues': issues,
        'code_reviews': code_reviews,
        'new_contributors': len(contributors)
    }

# Metrics Calculation Module
def calculate_metrics(raw_data):
    metrics = {}

    # Commit frequency
    commit_dates = [commit.commit.author.date for commit in raw_data['commits']]
    metrics['commit_frequency'] = len(commit_dates) / 30 if commit_dates else 0  # commits per day

    # PR merge rate
    if raw_data['pull_requests']:
        merged_prs = [pr for pr in raw_data['pull_requests'] if pr.merged]
        metrics['pr_merge_rate'] = len(merged_prs) / len(raw_data['pull_requests'])
    else:
        metrics['pr_merge_rate'] = 0

    # Issue resolution time
    closed_issues = [issue for issue in raw_data['issues'] if issue.closed_at]
    if closed_issues:
        resolution_times = [(issue.closed_at - issue.created_at).total_seconds() / 3600 for issue in closed_issues]
        metrics['avg_issue_resolution_time'] = sum(resolution_times) / len(resolution_times)
    else:
        metrics['avg_issue_resolution_time'] = 0

    # Code review turnaround time
    if raw_data['code_reviews']:
        review_times = [(review.submitted_at - review.created_at).total_seconds() / 3600 for review in raw_data['code_reviews']]
        metrics['avg_review_turnaround_time'] = sum(review_times) / len(review_times)
    else:
        metrics['avg_review_turnaround_time'] = 0

    # New contributors metric
    metrics['new_contributors'] = raw_data['new_contributors']

    return metrics

# Dashboard Visualization Module
def create_visualizations(metrics):
    
    if 'commit_frequency' in metrics:
        # Commit frequency chart
        commit_freq_fig = px.bar(
            x=['Commit Frequency'],
            y=[metrics['commit_frequency']],
            labels={'x': 'Metric', 'y': 'Commits per Day'},
            title='Average Daily Commit Frequency'
        )
        st.plotly_chart(commit_freq_fig)

    if 'pr_merge_rate' in metrics:
        # PR merge rate chart
        pr_merge_fig = px.pie(
            values=[metrics['pr_merge_rate'], 1 - metrics['pr_merge_rate']],
            names=['Merged', 'Not Merged'],
            title='Pull Request Merge Rate'
        )
        st.plotly_chart(pr_merge_fig)

    if 'avg_issue_resolution_time' in metrics:
        # Issue resolution time chart
        issue_time_fig = px.bar(
            x=['Average Issue Resolution Time'],
            y=[metrics['avg_issue_resolution_time']],
            labels={'x': 'Metric', 'y': 'Hours'},
            title='Average Issue Resolution Time'
        )
        st.plotly_chart(issue_time_fig)

    if 'avg_review_turnaround_time' in metrics:
        # Code review turnaround time chart
        review_time_fig = px.bar(
            x=['Average Review Turnaround Time'],
            y=[metrics['avg_review_turnaround_time']],
            labels={'x': 'Metric', 'y': 'Hours'},
            title='Average Code Review Turnaround Time'
        )
        st.plotly_chart(review_time_fig)

    if 'new_contributors' in metrics:
        # New contributors chart
        new_contributors_fig = px.bar(
            x=['New Contributors'],
            y=[metrics['new_contributors']],
            labels={'x': 'Metric', 'y': 'Count'},
            title='Number of New Contributors'
        )
        st.plotly_chart(new_contributors_fig)

# Natural Language Query Module
def process_query(query, metrics):
    query = query.lower()
    
    if 'commit' in query and 'frequency' in query:
        return f"The average daily commit frequency is {metrics['commit_frequency']:.2f} commits per day."
    
    elif 'pr' in query or 'pull request' in query:
        if 'merge' in query or 'rate' in query:
            return f"The pull request merge rate is {metrics['pr_merge_rate']:.2%}."
    
    elif 'issue' in query and ('resolution' in query or 'time' in query):
        return f"The average issue resolution time is {metrics['avg_issue_resolution_time']:.2f} hours."
    
    elif 'review' in query and 'time' in query:
        return f"The average code review turnaround time is {metrics['avg_review_turnaround_time']:.2f} hours."
    
    elif 'new contributors' in query:
        return f"The number of new contributors in the last 30 days is {metrics['new_contributors']}."
    
    else:
        return "I'm sorry, I couldn't understand your query. Please try asking about commit frequency, PR merge rate, issue resolution time, review turnaround time, or new contributors."

# Streamlit App
def main():
    st.title("GitHub Developer Performance Dashboard")

    # Input: GitHub repository URL
    repo_url = st.text_input("Enter GitHub repository URL:")

    if repo_url:
        # Collect data
        raw_data = collect_github_data(repo_url)

        if raw_data:  # Only proceed if raw_data is not None
            # Calculate metrics
            metrics = calculate_metrics(raw_data)

            # Create visualizations
            create_visualizations(metrics)

            # Natural language query interface
            query = st.text_input("Ask a question about the metrics:")
            if query:
                result = process_query(query, metrics)
                st.write(result)

if __name__ == "__main__":
    main()
