import streamlit as st
import csv
import math
import io

def prebonus_from_score(score):
    # Calculate the PreBonus based on the score according to given table logic.
    if score > 3.30:
        return 12000000
    index = int(math.floor(score * 100))
    return 1000000 + (index * 33333)

def process_data(file_content):
    # file_content is raw bytes from the uploaded file
    data_str = file_content.decode("utf-8")
    rows = list(csv.reader(io.StringIO(data_str)))

    # Attempt to detect header columns
    header = rows[0]
    if "Agent name" in header:
        name_col = header.index("Agent name")
        total_touch_col = header.index("Total Touch")
        total_valid_touch_col = header.index("Total Valid Touch")
        done_col = header.index("Valid Done")
        vendor_share_col = header.index("Average vendor Share")
        start_data = 1
    else:
        # Fallback column positions if no headers
        name_col = 0
        total_touch_col = 1
        total_valid_touch_col = 2
        done_col = 3
        vendor_share_col = 4
        start_data = 1

    agents = []
    pot = None

    # Parse rows
    for r in rows[start_data:]:
        # Ensure row has enough columns
        if len(r) <= vendor_share_col:
            continue

        name = r[name_col].strip()
        # Check if this might be the pot row (Agent name empty and pot in column F)
        if name == "":
            # Check column F (index 5)
            if len(r) > 5 and r[5].strip() != "":
                try:
                    pot = float(r[5].strip())
                except:
                    pass
            continue

        # Parse agent data
        try:
            total_touch = float(r[total_touch_col])
            valid_touch = float(r[total_valid_touch_col])
            done = float(r[done_col])
            vendor_share = float(r[vendor_share_col])
        except:
            continue

        agents.append({
            "name": name,
            "total_touch": total_touch,
            "valid_touch": valid_touch,
            "done": done,
            "vendor_share": vendor_share
        })

    if pot is None:
        raise ValueError("Pot value (F9) not found in CSV.")

    sum_total_touch = sum(a["total_touch"] for a in agents)
    sum_valid_touch = sum(a["valid_touch"] for a in agents)
    sum_done = sum(a["done"] for a in agents)
    sum_vendor_share = sum(a["vendor_share"] for a in agents)

    # Compute metrics for each agent
    for a in agents:
        a["X"] = a["total_touch"] / sum_total_touch if sum_total_touch != 0 else 0
        a["Y"] = a["valid_touch"] / sum_valid_touch if sum_valid_touch != 0 else 0
        a["U"] = a["done"] / sum_done if sum_done != 0 else 0
        a["J"] = a["vendor_share"] / sum_vendor_share if sum_vendor_share != 0 else 0
        a["K"] = a["done"] / a["total_touch"] if a["total_touch"] != 0 else 0
        a["O"] = a["done"] / a["valid_touch"] if a["valid_touch"] != 0 else 0
        a["Score"] = a["X"]*2 + a["Y"]*3 + a["U"]*10 + a["J"]*7

    # Rank by done (B)
    sorted_by_done = sorted(agents, key=lambda x: x["done"], reverse=True)
    for rank, agent_data in enumerate(sorted_by_done, start=1):
        agent_data["B"] = rank
    done_ranks = {a["name"]: a["B"] for a in sorted_by_done}
    for a in agents:
        a["B"] = done_ranks[a["name"]]

    max_B = max(a["B"] for a in agents) if agents else 1
    max_K = max(a["K"] for a in agents) if agents else 1
    max_O = max(a["O"] for a in agents) if agents else 1

    # PreBonus
    for a in agents:
        a["PreBonus"] = prebonus_from_score(a["Score"])

    # Distribution calculation
    denom = 0.0
    for a in agents:
        val = ((max_B - a["B"] + 1)**1.5
              + (max_K - a["K"] + 1)**1.5
              + (max_O - a["O"] + 1)**1.5)
        denom += val

    for a in agents:
        numerator = ((max_B - a["B"] + 1)**1.5
                    + (max_K - a["K"] + 1)**1.5
                    + (max_O - a["O"] + 1)**1.5)
        dist = pot * (numerator / denom) if denom != 0 else 0
        a["Distribution"] = dist
        a["FinalBonus"] = a["PreBonus"] + dist

    # Prepare output CSV with updated headers
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Agent",
        "Touch Score",          # was X
        "Valid Touch Score",    # was Y
        "Done Score",           # was U
        "Vendor Share Score",   # was J
        "Done Rank",            # was B
        "Conversion Rate",      # was K
        "Done Ratio",           # was O
        "Score",
        "PreBonus",
        "Distribution",
        "FinalBonus"
    ])
    for a in agents:
        writer.writerow([
            a["name"],
            a["X"],
            a["Y"],
            a["U"],
            a["J"],
            a["B"],
            a["K"],
            a["O"],
            a["Score"],
            a["PreBonus"],
            a["Distribution"],
            a["FinalBonus"]
        ])

    return output.getvalue()


# Streamlit App Code
st.title("Agent Bonus Calculator Dashboard")

uploaded_file = st.file_uploader("Upload the input CSV file", type=["csv"])

if uploaded_file is not None:
    try:
        result_csv = process_data(uploaded_file.getvalue())
        st.success("Processing complete! Click the button below to download the results.")
        st.download_button(
            label="Download Output CSV",
            data=result_csv,
            file_name="output.csv",
            mime="text/csv"
        )
    except Exception as e:
        st.error(f"Error processing file: {e}")
