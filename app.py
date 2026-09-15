import streamlit as st
from agent import create_brochure

st.title('Generador de Folletos Corporativos con IA')
st.caption("**Nota:** Para optimizar la latencia y el consumo de tokens en esta demo, el folleto se genera en un formato Markdown ligero de hasta 200 palabras por sección.")

company = st.text_input('Nombre de la Empresa', value='Anthropic')
url = st.text_input('URL del sitio web', value='https://www.anthropic.com')

if st.button('Generar Folleto', width='stretch'):
    with st.spinner('Analizando sitio web y generando folleto...'):
        brochure_md = create_brochure(company, url)
        st.markdown(brochure_md)
