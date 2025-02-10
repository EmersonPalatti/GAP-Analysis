# Bibliotecas

import streamlit as st
import pandas as pd
import plotly.express as px
import os
from openai import OpenAI

# Page layout

st.set_page_config(layout='wide')

# Functions

## Function - Formatar Número
def formata_num(valor, prefixo = ''):
    for unidade in ['', 'K']:
        if valor < 1000:
            return f'{prefixo}{valor:.2f}{unidade}'
        valor /= 1000
    return f'{prefixo}{valor:.2f} M'

# Dataset

@st.cache_data(persist='disk')
def load_and_preprocess_data():
    df = pd.read_csv(r'F:\Scripts\GAP_Analysis\GAP Analysis.csv', sep=';', encoding='latin1')
    df = df.dropna()
    
    # Casting - Trocando o tipo de dado de algumas colunas
    for col in ['Quantity', 'Sales Price (converted)', 'Total Price (converted)']:
        df[col] = df[col].replace(',', '.', regex=True)
    df[['Quantity', 'Sales Price (converted)', 'Total Price (converted)']] = df[['Quantity', 'Sales Price (converted)', 'Total Price (converted)']].astype(float)
    
    df[['Created Date', 'Close Date']] = df[['Created Date', 'Close Date']].astype('datetime64[ns]')
    df['Year'] = df['Close Date'].dt.year
    
    return df

@st.cache_data(persist='disk')
def filter_longtail(df):
    return df[df['Account Name: Account Stratification: Customer Classification'] == 'Long Tail']

# Carregar e processar dados
df = load_and_preprocess_data()

# Filtragem para clientes classificados como Long Tail
df_longtail = filter_longtail(df)


st.title('Customers GAP Analysis')

# Sidebar filters

st.sidebar.title('Global Filters', help = 'Filters that will by applied to all charts')

with st.sidebar.expander('Date'):
    date_range = st.date_input('Select the date range', (df['Close Date'].min().date(), df['Close Date'].max().date()))
    if st.button('Reset Date'):
        date_range = (df['Close Date'].min().date(), df['Close Date'].max().date())    
    if date_range:
        start_date = pd.Timestamp(date_range[0])
        end_date = pd.Timestamp(date_range[1])
        df = df[(df['Close Date'] >= start_date) & (df['Close Date'] <= end_date)]

def filter_dataframe(df, column_name, label, session_state_var):
    with st.sidebar.expander(label):
        st.session_state[session_state_var] = st.session_state.get(session_state_var, False)
        if st.button(f'Select/Deselect All {label}'):
            st.session_state[session_state_var] = not st.session_state[session_state_var]
        
        selected_options = st.multiselect(
            label, 
            df[column_name].unique(), 
            default=df[column_name].unique() if st.session_state[session_state_var] else []
        )
        
        if selected_options:
            return df[df[column_name].isin(selected_options)]
        return df
    
## Aplicando os filtros
df = filter_dataframe(df, 'Legal Entity', 'Country', 'select_all_country')
df = filter_dataframe(df, 'Account Name: MM Industry', 'Industry', 'select_all_industry')
df = filter_dataframe(df, 'Account Name: Account Name', 'Customer', 'select_all_customers')
df = filter_dataframe(df, 'Account Name: Account Stratification: Customer Classification', 'Customer Classification', 'select_all_customer_classification')
df = filter_dataframe(df, 'Product Group', 'SBU - Group Code', 'select_all_sbu')
df = filter_dataframe(df, 'Price Book Entry: Product: Product Group Descrip', 'SBU - Group Name', 'select_all_sbu_names')
df = filter_dataframe(df, 'Price Book Entry: Product: Product Code', 'Product Code', 'select_all_product_code')
df = filter_dataframe(df, 'Price Book Entry: Product: Product Name', 'Product Name', 'select_all_product')

# Tables

## Renevue tables

### Monthly Revenue

m_revenue = df.set_index('Close Date').groupby(pd.Grouper(freq='M'))['Total Price (converted)'].sum().reset_index()
m_revenue['Year'] = m_revenue['Close Date'].dt.year
m_revenue['Month'] = m_revenue['Close Date'].dt.month_name()

### Yearly Revenue

sales_by_year = df.groupby(df['Close Date'].dt.year)['Total Price (converted)'].sum().reset_index()
sales_by_year = sales_by_year[(sales_by_year['Close Date'] >= 2020) & (sales_by_year['Close Date'] <= 2024)]

### Industry

segmented_sales = df.set_index('Close Date').groupby([pd.Grouper(freq='Y'), 'Account Name: MM Industry'])['Total Price (converted)'].sum().reset_index()


segmented_sales_23_24 = df.set_index('Close Date').groupby([pd.Grouper(freq='M'), 'Account Name: MM Industry'])['Total Price (converted)'].sum().reset_index()
segmented_sales_23_24 = segmented_sales_23_24[segmented_sales_23_24['Close Date'] >= '2024']

### Growth 

sales_by_year['Growth'] = (sales_by_year['Total Price (converted)'].pct_change() * 100).round(2)

### Top Customer

# top_customers = df.groupby('Account Name: Account Name')[['Total Price (converted)', 'Close Date']].sum().sort_values(ascending=False).head(10).reset_index()

top_customers = df.groupby('Account Name: Account Name').agg({
    'Total Price (converted)': 'sum',
    'Close Date': 'max'
}).sort_values('Total Price (converted)', ascending=False).reset_index()

top_customers_23_24 = top_customers[top_customers['Close Date'].dt.year.isin([2023, 2024])]

### Customer Annual Variation

# Graphs 

## Monthly Revenue

fig_m_revenue = px.line(
    m_revenue,
    x = 'Month',
    y = 'Total Price (converted)',
    markers=True,
    color = 'Year',
    title = 'Monthly Revenue',
    template = 'seaborn'
)
fig_m_revenue.update_layout(yaxis_title='Revenue')

### Monthly Revenue 2023-2024
fig_m_revenue_23_24 = px.line(
    m_revenue[m_revenue['Year'].isin([2024])],
    x = 'Month',
    y = 'Total Price (converted)',
    markers=True,
    color = 'Year',
    title = 'Monthly Revenue',
    template = 'seaborn',
)
fig_m_revenue_23_24.update_layout(yaxis_title='Revenue')

## Yearly Revenue

fig_sales_historical = px.line(
    sales_by_year,
    x='Close Date',
    y='Total Price (converted)',
    markers=True,
    title='Sales Historical',
    labels={'Close Date': 'Year', 'Total Price (converted)': 'Total Sales'},
    template='seaborn',
    text=sales_by_year['Total Price (converted)'].apply(formata_num)
)
fig_sales_historical.update_layout(
    yaxis_title='Total Sales',
    xaxis_title='Year',
    xaxis=dict(tickmode='linear', dtick=1)
)

### Yearly Revenue - 2023-2024

fig_sales_historial_23_24 = px.bar(
    sales_by_year[sales_by_year['Close Date'].isin([2024])],
    x='Close Date',
    y='Total Price (converted)',
    # markers=True,
    text_auto=True,
    title='Sales Historical',
    labels={'Close Date': 'Year', 'Total Price (converted)': 'Total Sales'},
    template='seaborn',
    # text=sales_by_year['Total Price (converted)'].apply(formata_num)
    )
fig_sales_historial_23_24.update_layout(
    yaxis_title='Total Sales',
    xaxis_title='Year',
    xaxis=dict(tickmode='linear', dtick=1)
)

## Industry 

fig_segmented_sales = px.line(
    segmented_sales, 
    x='Close Date', 
    y='Total Price (converted)', 
    color='Account Name: MM Industry', 
    title='Sales by Industry',
    template='seaborn')
fig_segmented_sales.update_layout(yaxis_title='Total Sales', xaxis_title='Year')    

### Industry - 2023-2024

fig_segmented_sales_23_24 = px.line(
    data_frame=segmented_sales_23_24, 
    x='Close Date', 
    y='Total Price (converted)', 
    color='Account Name: MM Industry', 
    title='Sales by Industry (Monthly)',
    template='seaborn')
fig_segmented_sales_23_24.update_layout(yaxis_title='Total Sales', xaxis_title='Year')

## Growth

fig_growth = px.bar(
    sales_by_year, 
    x='Close Date', 
    y='Growth', 
    title='Year-over-Year Sales Growth',
    template='seaborn',
    text_auto=True,
    # text=sales_by_year['Total Price (converted)'].apply(formata_num)
    )
fig_growth.update_layout(yaxis_title='Growth (%)', xaxis_title='Year')

### Growth - 2023-2024

fig_growth_23_24 = px.bar(
    sales_by_year[sales_by_year['Close Date'].isin([2023, 2024])], 
    x='Close Date', 
    y='Growth', 
    title='Year-over-Year Sales Growth (2023 compared to 2024)',
    template='seaborn',
    text_auto=True,
    # text=sales_by_year['Total Price (converted)'].apply(formata_num)
    )
fig_growth_23_24.update_layout(yaxis_title='Growth (%)', xaxis_title='Year')


## Customers

fig_top_customers = px.bar(
    data_frame=top_customers.head(10),
    x='Account Name: Account Name', 
    y='Total Price (converted)', 
    title='Top 10 Customers by Total Sales',
    text_auto=True,
    template='seaborn')
fig_top_customers.update_layout(yaxis_title='Total Sales', xaxis_title='Customer')

### Customer - 2023-2024

fig_top_customers_23_24 = px.bar(
    top_customers_23_24.head(10),
    x='Account Name: Account Name', 
    y='Total Price (converted)', 
    title='Top 10 Customers by Total Sales (2024)',
    text_auto=True,
    template='seaborn')
fig_top_customers_23_24.update_layout(yaxis_title='Total Sales', xaxis_title='Customer')

# Longtail Analysis

# Monthly Revenue
m_revenue_longtail = df_longtail.set_index('Close Date').groupby(pd.Grouper(freq='M'))['Total Price (converted)'].sum().reset_index()
m_revenue_longtail['Year'] = m_revenue_longtail['Close Date'].dt.year
m_revenue_longtail['Month'] = m_revenue_longtail['Close Date'].dt.month_name()

fig_m_revenue_longtail = px.line(
    m_revenue_longtail,
    x='Month',
    y='Total Price (converted)',
    markers=True,
    color='Year',
    title='Monthly Revenue (Long Tail Customers)',
    template='seaborn'
)
fig_m_revenue_longtail.update_layout(yaxis_title='Revenue')

# Yearly Revenue
sales_by_year_longtail = df_longtail.groupby(df_longtail['Close Date'].dt.year)['Total Price (converted)'].sum().reset_index()
sales_by_year_longtail = sales_by_year_longtail[(sales_by_year_longtail['Close Date'] >= 2020) & (sales_by_year_longtail['Close Date'] <= 2024)]

fig_sales_historical_longtail = px.line(
    sales_by_year_longtail,
    x='Close Date',
    y='Total Price (converted)',
    markers=True,
    title='Sales Historical (Long Tail Customers)',
    labels={'Close Date': 'Year', 'Total Price (converted)': 'Total Sales'},
    template='seaborn',
    text=sales_by_year_longtail['Total Price (converted)'].apply(lambda x: f'{x:.2f}')
)
fig_sales_historical_longtail.update_layout(
    yaxis_title='Total Sales',
    xaxis_title='Year',
    xaxis=dict(tickmode='linear', dtick=1)
)

# Industry
segmented_sales_longtail = df_longtail.set_index('Close Date').groupby([pd.Grouper(freq='Y'), 'Account Name: MM Industry'])['Total Price (converted)'].sum().reset_index()

fig_segmented_sales_longtail = px.line(
    segmented_sales_longtail, 
    x='Close Date', 
    y='Total Price (converted)', 
    color='Account Name: MM Industry', 
    title='Sales by Industry (Long Tail Customers)',
    template='seaborn'
)
fig_segmented_sales_longtail.update_layout(yaxis_title='Total Sales', xaxis_title='Year')    

# Growth
sales_by_year_longtail['Growth'] = (sales_by_year_longtail['Total Price (converted)'].pct_change() * 100).round(2)

fig_growth_longtail = px.bar(
    sales_by_year_longtail, 
    x='Close Date', 
    y='Growth', 
    title='Year-over-Year Sales Growth (Long Tail Customers)',
    template='seaborn',
    text_auto=True
)
fig_growth_longtail.update_layout(yaxis_title='Growth (%)', xaxis_title='Year')

# Top Customer
top_customers_longtail = df_longtail.groupby('Account Name: Account Name').agg({
    'Total Price (converted)': 'sum',
    'Close Date': 'max'
}).sort_values('Total Price (converted)', ascending=False).reset_index()

fig_top_customers_longtail = px.bar(
    data_frame=top_customers_longtail.head(10),
    x='Account Name: Account Name', 
    y='Total Price (converted)', 
    title='Top 10 Long Tail Customers by Total Sales',
    text_auto=True,
    template='seaborn'
)
fig_top_customers_longtail.update_layout(yaxis_title='Total Sales', xaxis_title='Customer')


# Tabs

tab1, tab2, tab3 = st.tabs(['All Time', 'Monthly Analysis of 2024', 'Long Tail Analysis'])

with tab1:
    col1, col2 = st.columns(2)
    with col1:
        st.plotly_chart(fig_m_revenue, use_container_width=True, key='m_revenue')
        st.plotly_chart(fig_sales_historical, use_container_width=True, key='sales_historical')
    st.plotly_chart(fig_top_customers, use_container_width=True, key='top_customers')

    with col2:
        st.plotly_chart(fig_segmented_sales, use_container_width=True, key='segmented_sales')
        st.plotly_chart(fig_growth, use_container_width=True, key='growth')

with tab2:
    col1, col2 = st.columns(2)
    with col1:
        st.plotly_chart(fig_m_revenue_23_24, use_container_width=True, key='m_revenue_23_24')
        st.plotly_chart(fig_sales_historial_23_24, use_container_width=True, key='sales_historial_23_24')
    st.plotly_chart(fig_top_customers_23_24, use_container_width=True, key='top_customers_23_24')
    with col2:
        st.plotly_chart(fig_segmented_sales_23_24, use_container_width=True, key='segmented_sales_23_24')
        st.plotly_chart(fig_growth_23_24, use_container_width=True, key='growth_23_24')

with tab3:  # Assumindo que você adicionou um terceiro tab para Long Tail Analysis
    col1, col2 = st.columns(2)
    with col1:
        st.plotly_chart(fig_m_revenue_longtail, use_container_width=True, key='m_revenue_longtail')
        st.plotly_chart(fig_sales_historical_longtail, use_container_width=True, key='sales_historical_longtail')
    with col2:
        st.plotly_chart(fig_segmented_sales_longtail, use_container_width=True, key='segmented_sales_longtail')
        st.plotly_chart(fig_growth_longtail, use_container_width=True, key='growth_longtail')
    st.plotly_chart(fig_top_customers_longtail, use_container_width=True, key='top_customers_longtail')
 
