import streamlit as st
import pandas as pd
import plotly.express as px
from pathlib import Path

def satting_list():
    """PAGE SETUP"""
    st.set_page_config(page_title="Analytics Moscow Exchange | Portfolio", page_icon="📈", layout="wide")
    st.title("📈 Interactive Dashboard: Moscow Exchange Foreign Exchange Market")
    # Neat small subtitle (built-in Streamlit function)
    st.caption("The interactive dashboard is built on real trading data.")
    # A subtle visual separator line
    st.markdown("---")

def load_dash():
    """Data loading function with automatic caching and date lookup."""
    current_folder = Path(__file__).parent
    # The correct path to the file relative to the folder with the scriptм
    file_path = current_folder / "Data Chest" / "Moscow Exchange_currency_daily2.csv"
    if not file_path.exists():
        return None
    df = pd.read_csv(file_path, encoding="utf-8")

    date_col = None
    # We automatically locate the date column and convert it to the correct data type.
    for col in df.columns:
        if any(keyword in col.lower() for keyword in ['date', 'дата', 'time']):
            df[col] = pd.to_datetime(df[col], errors='coerce')
            df = df.sort_values(by=col).reset_index(drop=True)
            date_col = col
            break
    return df, date_col

def poisk_znach(df):
    """Searching for values for everything, side panel charts, and so on"""
    # numerical values
    numeric_cols = list(df.select_dtypes(include=['number']).columns)
    if not numeric_cols:
        st.error("No numerical columns for analysis were found in the dataset.")
        st.stop()
    default_y = numeric_cols[0]
    for col in numeric_cols:
        if any(x in col.lower() for x in ['close', 'закр', 'price', 'курс', 'значен']):
            default_y = col
            break
    return default_y, numeric_cols

def bocl_panel(default_y, numeric_cols, df, date_col):
    """SIDE FILTER PANEL"""
    st.sidebar.header('"🎛️ Data filters"')
    y_axis = st.sidebar.selectbox("Key indicator for analysis:", options=numeric_cols,
                                  index=numeric_cols.index(default_y))
    # 2. Range filter for the selected metric
    min_val, max_val = float(df[y_axis].min()), float(df[y_axis].max())
    selected_range = st.sidebar.slider(f"Range of values ({y_axis}):", min_value=min_val, max_value=max_val,
                                       value=(min_val, max_val))
    # 3. Filter by date
    filtered_df = df.copy()
    if date_col:
        min_date = df[date_col].min().to_pydatetime()
        max_date = df[date_col].max().to_pydatetime()
        selected_dates = st.sidebar.slider("Time period:", value=(min_date, max_date), min_value=min_date,
                                           max_value=max_date)
        # Protection against a Streamlit bug (occurring when a user has clicked only the first
        # date but has not yet selected the second)
        if isinstance(selected_dates, tuple) and len(selected_dates) == 2:
            start_date, end_date = selected_dates
            filtered_df = filtered_df[(filtered_df[date_col] >= pd.to_datetime(start_date)) &
                                      (filtered_df[date_col] <= pd.to_datetime(end_date))]
    # Applying a filter based on the slider (corrected using selected_range[0] and [1])
    filtered_df = filtered_df[filtered_df[y_axis].between(selected_range[0], selected_range[1])]
    return y_axis, filtered_df

def metrick(filtered_df, y_axis):
    """Displaying key performance indicators (metrics) based on filtered data"""
    if filtered_df.empty:
        st.warning("No data matches the selected filters.")
    else:
        st.subheader("📊 Key indicators for the period")
        col1, col2, col3, col4 = st.columns(4)

        current_val = filtered_df[y_axis].iloc[-1]
        min_period = filtered_df[y_axis].min()
        max_period = filtered_df[y_axis].max()

        # Calculation of the change (delta) relative to the beginning of the selected period
        if len(filtered_df) > 1:
            first_val = filtered_df[y_axis].iloc[0]
            delta_val = current_val - first_val
            # Added a check for 0 so that the code doesn't crash if the first price is zero.
            delta_pct = (delta_val / first_val) * 100 if first_val != 0 else 0
            delta_str = f"{delta_val:+.2f} ({delta_pct:+.2f}%)"
        else:
            delta_str = None

        with col1:
            st.metric("Total trading days", len(filtered_df))
        with col2:
            st.metric("Current value", f"{current_val:,.2f}", delta=delta_str)
        with col3:
            st.metric("Minimum for the period", f"{min_period:,.2f}")
        with col4:
            st.metric("Maximum for the period", f"{max_period:,.2f}")

        st.markdown("---")

def grafic(filtered_df, date_col, y_axis):
    """Creating charts"""
    layout_col1, layout_col2 = st.columns(2)

    with layout_col1:
        st.subheader(f"Indicator dynamics")
        if date_col:
            fig_line = px.line(filtered_df, x=date_col, y=y_axis, title=f"Time series of values {y_axis}",
                               template="plotly_white")
            fig_line.update_layout(xaxis_title="Date", yaxis_title=y_axis)
            st.plotly_chart(fig_line, use_container_width=True)
        else:
            st.info("The dynamics chart is not available (the date column is missing).")

    with layout_col2:
        st.subheader("Distribution of values (Histogram)")
        fig_hist = px.histogram(filtered_df, x=y_axis, nbins=30, title=f"Frequency distribution of levels {y_axis}",
                                color_discrete_sequence=["#1f77b4"], template="plotly_white")
        fig_hist.update_layout(xaxis_title=y_axis, yaxis_title="Number of days")
        st.plotly_chart(fig_hist, use_container_width=True)

    st.markdown("---")
    layout_col3, layout_col4 = st.columns(2)

    with layout_col3:
        st.subheader("Analysis of dispersion (Box Plot)")
        fig_box = px.box(filtered_df, y=y_axis, points="all", title=f"Median and quartiles {y_axis}",
                         color_discrete_sequence=["#2ca02c"], template="plotly_white")
        st.plotly_chart(fig_box, use_container_width=True)

    with layout_col4:
        st.subheader("Top 10 days with the highest values")
        top_days = filtered_df.nlargest(10, y_axis)
        x_bar = date_col if date_col else top_days.index

        fig_bar = px.bar(top_days, x=x_bar, y=y_axis, color=y_axis, title=f"Peak values {y_axis} over the period",
                         template="plotly_white")
        st.plotly_chart(fig_bar, use_container_width=True)

def tabl_data(df, date_col):
    """Data table"""
    st.markdown("---")
    st.subheader('📋 Initial trading data')
    # If you find a column with a date, sort by it (with the most recent entries at the top).
    if date_col:
        df_table_show = df.sort_values(date_col, ascending=False)
    else:
        df_table_show = df
    st.dataframe(df_table_show, use_container_width=True)

def main():
    """ main function """
    satting_list()
    df, date_col = load_dash()
    default_y, numeric_cols = poisk_znach(df)
    y_axis, filtered_df = bocl_panel(default_y, numeric_cols, df, date_col)
    metrick(filtered_df, y_axis)
    grafic(filtered_df, date_col, y_axis)
    tabl_data(df, date_col)


if __name__ == '__main__':
    main()
