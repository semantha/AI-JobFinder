import pandas as pd
import semantha_sdk
import semanthaAuth
import streamlit as st
import json
import requests
import numpy as np
from st_aggrid import GridOptionsBuilder, AgGrid, GridUpdateMode, DataReturnMode
from io import BytesIO
import streamlit.components.v1 as components
from st_custom_components import st_audiorec
import cv2 as cv
from PIL import Image

server = 'local'
domain = 'HR'

#semantha = semantha_sdk.login(semanthaAuth.platform_url[server], semanthaAuth.sdk_auth[server])


def similarity_matrix (server, domain, file, threshold):
    url_base = semanthaAuth.server_url[server]
    authorization = semanthaAuth.server_auth[server]
    url = f'{url_base}/tt-platform-server/api/domains/{domain}/similaritymatrix'
    headers = {
        'Accept': 'application/json',
        'Authorization': str(authorization)
    }
    files = [
        ('file', ('test.pdf', file, 'application/pdf'))
    ]
    payload = {
        'tags': 'JD',
        'similaritythreshold': str(threshold)
    }
    response = requests.request("POST", url, headers=headers, data=payload, files=files).json()
    return response


@st.cache_data(show_spinner="Finding your perfect job")
def get_matches(file):
    bytes_file = file.getvalue()
    matches_list = {
        "job_title": [],
        "score": [],
        "documentId": []
    }
    matrix_response = similarity_matrix(server, domain, bytes_file, "0.7")
    for element in matrix_response:
        references = element['references']
        for element2 in references:
            matches_list['job_title'].append(element2['documentName'])
            matches_list['score'].append(element2['similarity'])
            matches_list['documentId'].append(element2['documentId'])

    data = pd.DataFrame(matches_list)
    data.sort_values(by='score', inplace=True, ascending=False)
    data['url'] = [None] * len(data['job_title'])
    data['salary'] = [None] * len(data['job_title'])
    data['location'] = [None] * len(data['job_title'])
    if file == 0:
        return 0
    else:
        return data


def get_metadata(server, domain, data):
    url_base = semanthaAuth.server_url[server]
    authorization = semanthaAuth.server_auth[server]
    url = f'{url_base}/tt-platform-server/api/domains/{domain}/referencedocuments/{data[2]}'
    headers = {
        'Accept': 'application/json',
        'Authorization': str(authorization)
    }
    response = requests.request("GET", url, headers=headers).json()
    if "metadata" in response:
        metadata = json.loads(response["metadata"])
        data[3] = metadata["url"]
        data[4] = metadata["salary"]
        data[5] = metadata["location"]
    return data


def get_video(server, domain, string):
    url_base = semanthaAuth.server_url[server]
    authorization = semanthaAuth.server_auth[server]
    references_url = f'{url_base}/tt-platform-server/api/domains/{domain}/references?maxreferences=1'
    headers = {
        'Accept': 'application/json',
        'Authorization': str(authorization)
    }
    payload = {
        'similaritythreshold': '0.7',
    }
    files = [
        ('text', (None, string))
    ]
    references_response = requests.request("POST", references_url, headers=headers, data=payload, files=files).json()
    #st.write(references_response)
    if 'references' in references_response:
        match_id = references_response["references"][0]["documentId"]
        referencedocuments_url = f'{url_base}/tt-platform-server/api/domains/{domain}/referencedocuments/{match_id}'
        referencedocuments_response = requests.request("GET", referencedocuments_url, headers=headers).json()
        #st.write(referencedocuments_response)
        text = referencedocuments_response["pages"][0]["contents"][0]["paragraphs"][0]["sentences"][0]["text"]
        metadata = json.loads(referencedocuments_response["metadata"])
        video_url = metadata["url"]
        start_time = round(metadata["start"]/1000)
        return video_url, start_time, text
    else:
        return 0


st.image(Image.open('C:\\Users\\josep\\PycharmProjects\\streamlit_CV\\Semantha-positiv-RGB.png'))

# define session states
if 'bumblebee_search' not in st.session_state:
    st.session_state['bumblebee_search'] = None
if 'cv_input_format' not in st.session_state:
    st.session_state['cv_input_format'] = None
if 'cv_compare' not in st.session_state:
    st.session_state['cv_compare'] = None
if 'cv_all_results' not in st.session_state:
    st.session_state['cv_all_results'] = None

bumblebee, cv = st.tabs([":bee: Bumblebee", ":page_with_curl: CV Matching"])
with bumblebee:
    st.title("semantha Bumblebee")
    st.markdown('***')
    st.write('Enter a sentence and semantha will search her music library for a line from a song that has similar meaning!')
    st.markdown('***')
    search_text = st.text_input("Search string:")
    search = st.button("Search")
    if search:
        st.session_state['bumblebee_search'] = True
    if st.session_state['bumblebee_search'] and search_text is not None:
        st.markdown('***')
        video_url = get_video(server, 'AI_Festival', search_text)
        if video_url == 0:
            st.write("No matches found")
        else:
            st.write("semantha has found the line")
            col1, col2 = st.columns((1, 10))
            with col2:
                st.markdown(f'<span style="font-style:italic;">...{video_url[2]}...</span>', unsafe_allow_html=True)
            st.write("and here it is on youtube:")
            st.video(video_url[0], start_time=video_url[1])

with cv:
    st.title("Job search with semantha")
    st.markdown('***')
    st.write('semantha will find the perfect job for you by using AI to read and understand your CV.')
    st.write('Don\'t have a CV with you? Simply record a message or take a video describing what you\'re good at and '
             'semantha will use that!')
    st.markdown('***')

    #collect input

    st.title('Input')
    col1, col2, col3 = st.columns((1, 1, 1))
    with col1:
        cv_input = st.button('Upload your CV')
        if cv_input:
            st.session_state['cv_input_format'] = 'cv'
    with col2:
        audio_input = st.button('Record audio')
        if audio_input:
            st.session_state['cv_input_format'] = 'audio'
    with col3:
        video_input = st.button('Take a video')
        if video_input:
            st.session_state['cv_input_format'] = 'video'


    if st.session_state['cv_input_format'] == 'cv':
        file = st.file_uploader(" ", type=['pdf', 'docx'], accept_multiple_files=False)
    if st.session_state['cv_input_format'] == 'audio':
        file = st_audiorec()
        if file is not None:
            st.audio(file, format='audio/wav')
            file.save()
    if st.session_state['cv_input_format'] == 'video':
        file = st.camera_input('')

    if st.session_state['cv_input_format'] is not None:
        compare = st.button('Compare')
        if compare:
            st.session_state['cv_compare'] = compare

    if st.session_state['cv_compare'] and file is not None:
        st.markdown('***')
        data = get_matches(file)
        st.title('Your top 3 positions:')
        medals = [':first_place_medal:', ':second_place_medal:', ':third_place_medal:']
        for i in range(0, 3):
            col1, col2 = st.columns((1, 10))
            data.iloc[i] = get_metadata(server, domain, data.iloc[i])
            with col1:
                st.markdown(f'<span style="font-size:50px;">{medals[i]}</span>', unsafe_allow_html=True)
            with col2:
                st.markdown(f'<span style="font-size:35px;">{data.iloc[i, 0]}</span>', unsafe_allow_html=True)
                col2_1, col2_2, col2_3 = st.columns((1, 1, 1))
                with col2_1:
                    st.markdown(f'<span style="font-size:15px;">Salary: {data.iloc[i, 4]}</span>', unsafe_allow_html=True)
                with col2_2:
                    st.markdown(f'<span style="font-size:15px;">Location: {data.iloc[i, 5]}</span>', unsafe_allow_html=True)
                with col2_3:
                    st.markdown(f'<span style="font-size:15px;">[Go to job :arrow_forward:]({data.iloc[i, 3]})</span>', unsafe_allow_html=True)

        cv_all_results = st.button('Load all positions')
        if cv_all_results:
            st.session_state['cv_all_results'] = cv_all_results

        if st.session_state['cv_all_results']:
            for i in range(3, len(data)):
                data.iloc[i] = get_metadata(server, domain, data.iloc[i])
            display_data = data[['score', 'job_title', 'salary', 'location', 'url']]
            gb = GridOptionsBuilder.from_dataframe(display_data)
            gb.configure_default_column(filterable=True)
            gb.configure_pagination(paginationAutoPageSize=True, paginationPageSize=10)
            gb.configure_column("score", header_name='Score', sortable=True, width=75)
            gb.configure_column("job_title", header_name='Job Title', flex=1)
            gb.configure_column("salary", header_name='Salary', sortable=True, width=80)
            gb.configure_column("location", header_name='Location', filter=True, width=100)
            gb.configure_column("url", header_name='URL', width=100)
            gridOptions = gb.build()

            grid_response = AgGrid(
                display_data,
                gridOptions=gridOptions,
                data_return_mode='AS_INPUT',
                update_mode='MODEL_CHANGED',
                fit_columns_on_grid_load=False,
                enable_enterprise_modules=True,
                height=350,
                width='100%',
                reload_data=True
            )

            data = grid_response['data']
            selected = grid_response['selected_rows']
            data = pd.DataFrame(selected)
