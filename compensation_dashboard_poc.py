import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from io import BytesIO

# === SET PAGE CONFIG ===
st.set_page_config(page_title="Compensation Modeling", layout="wide")

# === PASSWORD PROTECTION ===
# Simple password check
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    st.title("🔒 Compensation Dashboard POC - Login")
    password = st.text_input("Enter Password:", type="password")
    
    if st.button("Login"):
        if password == "CompDemo2025":
            st.session_state.authenticated = True
            st.success("✅ Access granted! Refreshing...")
            st.rerun()
        else:
            st.error("❌ Incorrect password")
    
    st.info("This is a private proof of concept dashboard.")
    st.stop()

# If we get here, user is authenticated

# === LOAD DATA ===
@st.cache_data
def load_data():
    try:
        file_path = "Mock_Compensation_Data_2024_2025.xlsx"
        xl = pd.ExcelFile(file_path)
        data = {
            "PayBand_2024": xl.parse("PayBand_2024"),
            "Employees_2024": xl.parse("Employees_2024"),
            "PayBand_2025": xl.parse("PayBand_2025"),
            "Employees_2025": xl.parse("Employees_2025")
        }
        return data
    except FileNotFoundError:
        st.error("Excel file not found. Please make sure 'Mock_Compensation_Data_2024_2025.xlsx' is in the same directory.")
        return None

data = load_data()

if data is not None:
    # === SIDEBAR SELECTION ===
    year = st.sidebar.selectbox("Select Year", ["2024", "2025"])
    employee_df = data[f"Employees_{year}"]

    # === FILTERS ===
    with st.sidebar:
        st.markdown("### Filters")
        
        dept_filter = st.multiselect(
            "Department", 
            sorted(employee_df["Department"].unique()),
            help="Select one or more departments"
        )
        
        job_level_filter = st.multiselect(
            "Job Level", 
            sorted(employee_df["Job_Level"].unique()),
            help="Select one or more job levels"
        )
        
        gender_filter = st.multiselect(
            "Gender", 
            sorted(employee_df["Gender"].unique()),
            help="Select one or more genders"
        )
        
        ethnicity_filter = st.multiselect(
            "Ethnicity", 
            sorted(employee_df["Ethnicity"].unique()),
            help="Select one or more ethnicities"
        )
        
        # Add salary range filter
        st.markdown("### Salary Range")
        min_salary, max_salary = st.slider(
            "Base Salary Range:",
            min_value=int(employee_df["Base_Salary"].min()),
            max_value=int(employee_df["Base_Salary"].max()),
            value=(int(employee_df["Base_Salary"].min()), int(employee_df["Base_Salary"].max())),
            format="$%d"
        )
        
        # Add compa ratio filter
        min_compa, max_compa = st.slider(
            "Compa Ratio Range:",
            min_value=float(employee_df["Compa_Ratio"].min()),
            max_value=float(employee_df["Compa_Ratio"].max()),
            value=(float(employee_df["Compa_Ratio"].min()), float(employee_df["Compa_Ratio"].max())),
            step=0.1,
            format="%.1f"
        )

    # === APPLY FILTERS ===
    filtered_df = employee_df.copy()

    if dept_filter:
        filtered_df = filtered_df[filtered_df["Department"].isin(dept_filter)]
    if job_level_filter:
        filtered_df = filtered_df[filtered_df["Job_Level"].isin(job_level_filter)]
    if gender_filter:
        filtered_df = filtered_df[filtered_df["Gender"].isin(gender_filter)]
    if ethnicity_filter:
        filtered_df = filtered_df[filtered_df["Ethnicity"].isin(ethnicity_filter)]
    
    # Apply salary and compa ratio filters
    filtered_df = filtered_df[
        (filtered_df["Base_Salary"] >= min_salary) & 
        (filtered_df["Base_Salary"] <= max_salary) &
        (filtered_df["Compa_Ratio"] >= min_compa) & 
        (filtered_df["Compa_Ratio"] <= max_compa)
    ]

    # === METRICS ===
    st.title(f"💼 Compensation Dashboard POC - {year}")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Total Employees", len(filtered_df))
    with col2:
        st.metric("Average Compa Ratio", f"{filtered_df['Compa_Ratio'].mean():.2f}")
    with col3:
        st.metric("Employees Below Midpoint", f"{(filtered_df['Compa_Ratio'] < 1).mean()*100:.1f}%")
    with col4:
        st.metric("Employees Above Max", f"{(filtered_df['Compa_Ratio'] > 1.2).sum()}")

    st.markdown("---")

    # === ENHANCED DATA TABLE WITH SELECTION ===
    st.subheader("📋 Interactive Employee Table")
    
    # Allow users to select specific employees
    if len(filtered_df) > 0:
        # Display the interactive data editor with selection capabilities
        edited_df = st.data_editor(
            filtered_df,
            use_container_width=True,
            height=400,
            column_config={
                "Base_Salary": st.column_config.NumberColumn(
                    "Base Salary",
                    format="$%d"
                ),
                "Compa_Ratio": st.column_config.NumberColumn(
                    "Compa Ratio",
                    format="%.2f"
                ),
                "Select": st.column_config.CheckboxColumn(
                    "Select",
                    help="Select rows to include in download",
                    default=False
                )
            },
            column_order=["Select"] + [col for col in filtered_df.columns],
            hide_index=True
        )
        
        # Show selection summary
        if "Select" in edited_df.columns:
            selected_count = edited_df["Select"].sum()
            st.info(f"📊 Selected {selected_count} out of {len(filtered_df)} employees")
            
            # Create download data (selected rows or all if none selected)
            if selected_count > 0:
                download_df = edited_df[edited_df["Select"] == True].drop("Select", axis=1)
                download_label = f"📥 Download Selected Data ({selected_count} employees)"
            else:
                download_df = filtered_df
                download_label = f"📥 Download All Filtered Data ({len(filtered_df)} employees)"
        else:
            download_df = filtered_df
            download_label = f"📥 Download Filtered Data ({len(filtered_df)} employees)"
    else:
        st.warning("No employees match the current filter criteria.")
        download_df = filtered_df
        download_label = "📥 Download Data (No Results)"

    # === DOWNLOAD BUTTON ===
    def to_excel(dataframe):
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            dataframe.to_excel(writer, index=False, sheet_name='Filtered_Data')
        processed_data = output.getvalue()
        return processed_data

    if len(filtered_df) > 0:
        st.download_button(
            label=download_label,
            data=to_excel(download_df),
            file_name=f"Employee_Data_{year}_{len(download_df)}_records.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    # === CHARTS ===
    st.markdown("---")
    
    if len(filtered_df) > 0:
        # Compa Ratio by Job Level Chart (your original chart)
        st.subheader("📊 Compa Ratio Distribution by Job Level")
        fig1 = px.box(
            filtered_df,
            x="Job_Level",
            y="Compa_Ratio",
            color="Gender",
            points="all",
            title="Compa Ratio Spread by Job Level and Gender"
        )
        st.plotly_chart(fig1, use_container_width=True)

        # Additional charts
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Average Base Salary by Department")
            dept_avg = filtered_df.groupby("Department")["Base_Salary"].mean().reset_index()
            fig2 = px.bar(dept_avg, x="Department", y="Base_Salary", 
                         title="Average Salary by Department")
            fig2.update_layout(xaxis_tickangle=-45)
            st.plotly_chart(fig2, use_container_width=True)

        with col2:
            st.subheader("Compa Ratio Distribution")
            fig3 = px.histogram(filtered_df, x="Compa_Ratio", nbins=20, 
                              title="Compa Ratio Histogram")
            st.plotly_chart(fig3, use_container_width=True)

        # === YEAR COMPARISON FEATURE ===
        st.markdown("---")
        st.subheader("📈 Year-over-Year Comparison")
        
        if st.checkbox("Enable Year Comparison"):
            other_year = "2025" if year == "2024" else "2024"
            other_df = data[f"Employees_{other_year}"]
            
            # Apply same filters to other year
            other_filtered = other_df.copy()
            if dept_filter:
                other_filtered = other_filtered[other_filtered["Department"].isin(dept_filter)]
            if job_level_filter:
                other_filtered = other_filtered[other_filtered["Job_Level"].isin(job_level_filter)]
            if gender_filter:
                other_filtered = other_filtered[other_filtered["Gender"].isin(gender_filter)]
            if ethnicity_filter:
                other_filtered = other_filtered[other_filtered["Ethnicity"].isin(ethnicity_filter)]
            
            # Comparison metrics
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric(
                    f"Avg Compa Ratio ({year})", 
                    f"{filtered_df['Compa_Ratio'].mean():.2f}",
                    delta=f"{filtered_df['Compa_Ratio'].mean() - other_filtered['Compa_Ratio'].mean():.2f}"
                )
            
            with col2:
                st.metric(
                    f"Avg Base Salary ({year})", 
                    f"${filtered_df['Base_Salary'].mean():,.0f}",
                    delta=f"${filtered_df['Base_Salary'].mean() - other_filtered['Base_Salary'].mean():,.0f}"
                )
            
            with col3:
                st.metric(
                    f"Employee Count ({year})", 
                    len(filtered_df),
                    delta=f"{len(filtered_df) - len(other_filtered)}"
                )

    # === INSIGHTS ===
    st.markdown("---")
    st.subheader("🔍 Key Insights")
    
    if len(filtered_df) > 0:
        col1, col2 = st.columns(2)
        
        with col1:
            st.write("**Compensation Analysis:**")
            if len(filtered_df.groupby("Department")["Base_Salary"].mean()) > 0:
                highest_dept = filtered_df.groupby("Department")["Base_Salary"].mean().idxmax()
                st.write(f"• Highest paid department: {highest_dept}")
            st.write(f"• Average compa ratio: {filtered_df['Compa_Ratio'].mean():.2f}")
            st.write(f"• Employees below 0.8 compa ratio: {len(filtered_df[filtered_df['Compa_Ratio'] < 0.8])}")
            st.write(f"• Employees above 1.2 compa ratio: {len(filtered_df[filtered_df['Compa_Ratio'] > 1.2])}")
        
        with col2:
            st.write("**Demographic Analysis:**")
            for gender in filtered_df['Gender'].unique():
                count = len(filtered_df[filtered_df['Gender'] == gender])
                avg_salary = filtered_df[filtered_df['Gender'] == gender]['Base_Salary'].mean()
                st.write(f"• {gender}: {count} employees, avg salary: ${avg_salary:,.0f}")

else:
    st.info("Please add your Excel file to continue.")
    st.markdown("**Expected file:** `Mock_Compensation_Data_2024_2025.xlsx`")
    st.markdown("**Expected sheets:** `Employees_2024`, `Employees_2025`, `PayBand_2024`, `PayBand_2025`")