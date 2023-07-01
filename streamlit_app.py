import base64
import pandas as pd
import semantha_sdk
import streamlit as st
import json
from st_aggrid import GridOptionsBuilder, AgGrid, GridUpdateMode, DataReturnMode
from st_custom_components import st_audiorec
from PIL import Image
import io
import os
import speech_recognition as sr
import texts
import moviepy.editor as mp

display_texts = texts.display_texts

domain = st.secrets.semantha.domain

semantha = semantha_sdk.login(st.secrets.semantha.server_url, st.secrets.semantha.api_key)


# define session states
if 'language' not in st.session_state:
    st.session_state['language'] = "de"
if 'bumblebee_search' not in st.session_state:
    st.session_state['bumblebee_search'] = None
if 'cv_input_format' not in st.session_state:
    st.session_state['cv_input_format'] = None
if 'cv_compare' not in st.session_state:
    st.session_state['cv_compare'] = None
if 'cv_all_results' not in st.session_state:
    st.session_state['cv_all_results'] = None

file = None

language_options = {
    "Deutsch": "de",
    "English": "en"
}


def get_display_text(name):
    return display_texts[name][0][st.session_state["language"]]


st.set_page_config(page_icon=Image.open(os.path.join(os.path.dirname(__file__), "favicon.png")))

qr, logo, col1, col2 = st.columns((3, 8, 2, 2))
with col2:
    st.write("")
    st.write("")
    language_selection = st.selectbox("Language", options=(list(language_options.values())), label_visibility="collapsed")
    st.session_state["language"] = language_selection
with col1:
    st.write("")
    st.write("")
    st.write(get_display_text("language_option"))
with logo:
    st.image(Image.open(os.path.join(os.path.dirname(__file__), "Semantha-positiv-RGB.png")))
with qr:
    st.image(Image.open(os.path.join(os.path.dirname(__file__), "KI-Festival.png")))

@st.cache_data(show_spinner=False)
def get_matches(file):
    matches_list = {
        "job_title": [],
        "score": [],
        "documentId": []
    }
    if isinstance(file, str):
        text_id = semantha.domains(domain).referencedocuments.post(tags='Applicant', text=file)[0].id
        matrix_response = semantha.domains(domain).similaritymatrix.post(sourcedocumentids=text_id, similaritythreshold=0.01, tags='Job_Description', mode='fingerprint')
        semantha.domains(domain).referencedocuments(documentid=text_id).delete()
    else:
        matrix_response = semantha.domains(domain).similaritymatrix.post(file=file, similaritythreshold=0.01, tags='Job_Description', mode='fingerprint')
    #st.write(matrix_response)
    for reference in matrix_response[0].references:
        if reference.similarity > 0:
            matches_list['job_title'].append(reference.document_name)
            matches_list['score'].append(reference.similarity)
            matches_list['documentId'].append(reference.document_id)
    #st.write(matches_list)
    data = pd.DataFrame(matches_list)
    data.sort_values(by='score', inplace=True, ascending=False)
    data['url'] = [None] * len(data['job_title'])
    data['salary'] = [None] * len(data['job_title'])
    data['location'] = [None] * len(data['job_title'])
    if len(data) == 0:
        st.error("semantha didn't find any matches, please try a different file")
    else:
        return data


def get_job_metadata(data):
    document = semantha.domains(domain).referencedocuments.get(documentids=data[2], limit=1, offset=0).data[0]
    metadata = document.metadata
    if metadata is not None:
        metadata = json.loads(metadata)
        data[3] = metadata["url"]
        data[4] = metadata["salary"]
        data[5] = metadata["location"]
    return data


def get_video(string):
    input_file = io.BytesIO(string.encode('utf-8'))
    input_file.name = 'input.txt'
    references = semantha.domains(domain).references.post(file=input_file, similaritythreshold=0.01, tags='', maxreferences=1, mode='fingerprint')
    #st.write(references)
    if references.references is not None:
        reference_id = references.references[0].document_id
        referencedocuments_response = semantha.domains(domain).referencedocuments(documentid=reference_id).get()
        #st.write(referencedocuments_response)
        text = referencedocuments_response.pages[0].contents[0].paragraphs[0].text
        metadata = referencedocuments_response.metadata
        if metadata is not None:
            #st.write(metadata)
            metadata = json.loads(metadata)
            video_url = metadata["url"]
            start_time = round(metadata["start"]/1000)
            return video_url, start_time, text
        else:
            return 0
    else:
        return 0


def display_pdf(document):
    pdf_display = F'<center><iframe src="data:application/pdf;base64,{base64.b64encode(document.read()).decode("utf-8")}" width="600" height="800" type="application/pdf"></iframe></center>'
    st.markdown(pdf_display, unsafe_allow_html=True)
    file.seek(0, 0)

def transcribe_audio():
    languages = {
        "en": "en-EN",
        "de": "de-DE"
    }
    file_text = None
    audio_language = languages[language_selection]
    r = sr.Recognizer()
    audio = sr.AudioFile(os.path.join(os.path.dirname(__file__), 'audio.wav'))
    with audio as source:
        audio = r.record(source)
        try:
            file_text = r.recognize_google(audio, language=audio_language)
            file_text = st.text_input(get_display_text("cv_audio_output"), file_text)
        except:
            st.error(get_display_text("cv_audio_error"))
    return file_text


bumblebee, cv = st.tabs([":bee: Bumblebee", ":page_with_curl: CV Matching"])
with bumblebee:
    st.title(get_display_text("bumblebee_title"))
    st.markdown('***')
    st.header(get_display_text("how_it_works"))
    st.write(get_display_text("bumblebee_description"))
    st.markdown('***')
    user_input = st.text_input(f'{get_display_text("search")}:')
    if user_input != '':
        example = st.selectbox(get_display_text("bumblebee_example"), ("Es ist sehr heiß hier!", "Where is the party at?"), disabled=True)
    else:
        example = st.selectbox(get_display_text("bumblebee_example"), ("Es ist sehr heiß hier!", "Where is the party at?"))
    if user_input != '':
        search_text = user_input
    else:
        search_text = example
    _, _b, _ = st.columns([1, 1, 1])
    with _b:
        search = st.button(get_display_text("search"), type="primary", use_container_width=True)
    if search:
        st.session_state['bumblebee_search'] = True
    if st.session_state['bumblebee_search'] and search_text is not None:
        st.markdown('***')
        video_url = get_video(search_text)
        if video_url == 0:
            st.write(get_display_text("bumblebee_no_matches"))
        else:
            st.write(get_display_text("bumblebee_line"))
            col1, col2 = st.columns((1, 10))
            with col2:
                st.markdown(f'<span style="font-style:italic;">...{video_url[2]}...</span>', unsafe_allow_html=True)
            st.write(get_display_text("bumblebee_youtube"))
            st.video(video_url[0], start_time=video_url[1])
        st.session_state['bumblebee_search'] = None

with cv:
    st.title(get_display_text("cv_title"))
    _, logo, _ = st.columns([1, 2, 1])
    with logo:
        st.image(Image.open(os.path.join(os.path.dirname(__file__), "Kaarisma.png")))

    st.markdown('***')
    st.subheader(get_display_text("how_it_works"))
    st.write(get_display_text("cv_description"))
    st.markdown('***')

    #collect input

    st.title('Input')
    col1, col2 = st.columns((1, 1))
    with col1:
        cv_input = st.button(get_display_text("cv_cv_title"), type="primary", use_container_width=True)
        if cv_input:
            st.session_state['cv_input_format'] = 'cv'
            st.session_state['cv_compare'] = None
    with col2:
        text_input = st.button(get_display_text("cv_text_title"), type="primary", use_container_width=True)
        if text_input:
            st.session_state['cv_input_format'] = 'text'
            st.session_state['cv_compare'] = None
    col1, col2 = st.columns((1, 1))
    with col1:
        audio_input = st.button(get_display_text("cv_audio_title"), type="primary", use_container_width=True)
        if audio_input:
            st.session_state['cv_input_format'] = 'audio'
            st.session_state['cv_compare'] = None
    with col2:
        video_input = st.button(get_display_text("cv_video_title"), type="primary", use_container_width=True)
        if video_input:
            st.session_state['cv_input_format'] = 'video'
            st.session_state['cv_compare'] = None

    st.markdown('***')

    if st.session_state['cv_input_format'] == 'cv':
        st.title(get_display_text("cv_cv_title"))
        uploaded_file = st.file_uploader(" ", type=['pdf', 'docx'], accept_multiple_files=False)
        if st.session_state["language"] == "en":
            demo_file = open(os.path.join(os.path.dirname(__file__), "Demo_CV.pdf"), "rb")
        if st.session_state["language"] == "de":
            demo_file = open(os.path.join(os.path.dirname(__file__), "Demo_Lebenslauf.pdf"), "rb")
        st.info(get_display_text("cv_demo_cv"))
        if uploaded_file is None:
            file = demo_file
        else:
            file = uploaded_file
        #display_pdf(file)
    if st.session_state['cv_input_format'] == 'text':
        st.title(get_display_text("cv_text_title"))
        st.write(get_display_text("cv_text_description_1"))
        st.write(get_display_text("cv_text_description_2"), unsafe_allow_html=True)
        text_input = st.text_input(f'{get_display_text("cv_text_input")}:')
        if text_input is not '':
            file = text_input
    if st.session_state['cv_input_format'] == 'audio':
        st.title(get_display_text("cv_audio_title"))
        st.write(get_display_text("cv_audio_description_1"))
        st.write(get_display_text("cv_audio_description_2"), unsafe_allow_html=True)
        st.markdown("***")
        audio_wav = st_audiorec()
        if audio_wav is not None:
            with open(os.path.join(os.path.dirname(__file__), "audio.wav"), mode='wb') as f:
                f.write(audio_wav)
            with st.spinner(get_display_text("cv_transcribing_spinner")):
                file = transcribe_audio()
                os.remove(os.path.join(os.path.dirname(__file__), "audio.wav"))

    if st.session_state['cv_input_format'] == 'video':
        st.title(get_display_text("cv_video_title"))
        st.write(get_display_text("cv_video_description_1"))
        st.write(get_display_text("cv_video_description_2"), unsafe_allow_html=True)

        uploaded_video_file = st.file_uploader(" ", type=['mp4'], accept_multiple_files=False)
        if uploaded_video_file is not None:
            with st.spinner(get_display_text("cv_transcribing_spinner")):
                with open(os.path.join(os.path.dirname(__file__), "video.mp4"), "wb") as f:
                    f.write(uploaded_video_file.getbuffer())
                    video_file = mp.VideoFileClip(os.path.join(os.path.dirname(__file__), "video.mp4"))
                    video_file.audio.write_audiofile(os.path.join(os.path.dirname(__file__), "audio.wav"))
                    video_file.close()
                file = transcribe_audio()
                os.remove(os.path.join(os.path.dirname(__file__), "audio.wav"))
                os.remove(os.path.join(os.path.dirname(__file__), "video.mp4"))

        #app_deepspeech.main()


    if st.session_state['cv_input_format'] is not None and file is not None:
        _, _b, _ = st.columns([1, 4, 1])
        with _b:
            compare = st.button(get_display_text("cv_analyse"), type="primary", use_container_width=True)
        if compare:
            st.session_state['cv_compare'] = compare
            st.session_state['cv_all_results'] = None

    if st.session_state['cv_compare'] and file is not None:
        st.markdown('***')
        with st.spinner(get_display_text("compare_spinner")):
            data = get_matches(file)
        if data is not None:
            st.title(get_display_text("cv_top_3"))
            medals = [':first_place_medal:', ':second_place_medal:', ':third_place_medal:']
            for i in range(0, 3):
                col1, col2 = st.columns((1, 10))
                data.iloc[i] = get_job_metadata(data.iloc[i])
                with col1:
                    st.markdown(f'<span style="font-size:50px;">{medals[i]}</span>', unsafe_allow_html=True)
                with col2:
                    st.markdown(f'<span style="font-size:35px;">{data.iloc[i, 0]}</span>', unsafe_allow_html=True)
                    col2_1, col2_2, col2_3 = st.columns((1, 1, 1))
                    with col2_1:
                        st.markdown(f'<span style="font-size:15px;">{get_display_text("cv_salary")}: {data.iloc[i, 4]}</span>', unsafe_allow_html=True)
                    with col2_2:
                        st.markdown(f'<span style="font-size:15px;">{get_display_text("cv_location")}: {data.iloc[i, 5]}</span>', unsafe_allow_html=True)
                    with col2_3:
                        st.markdown(f'<span style="font-size:15px;">[{get_display_text("cv_link")} :arrow_forward:]({data.iloc[i, 3]})</span>', unsafe_allow_html=True)
            _, _, _b = st.columns([1, 2, 1])
            with _b:
                cv_all_results = st.button(get_display_text("cv_load_all"), type="primary")
            if cv_all_results:
                st.session_state['cv_all_results'] = cv_all_results

            if st.session_state['cv_all_results']:
                for i in range(3, len(data)):
                    data.iloc[i] = get_job_metadata(data.iloc[i])
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
