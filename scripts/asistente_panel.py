"""Panel del asistente de IA generativa soberana para el deck del jurado."""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
from pathlib import Path

VERDE="#1B5E20"; VERDE2="#2E7D32"; AZUL="#0277BD"; AZUL2="#01579B"
TINTA="#12261A"; FONDO="#F6FAF6"; BORDE="#DCE8DF"; GRIS="#52645A"

fig=plt.figure(figsize=(15,9.7),dpi=100); fig.patch.set_facecolor(FONDO)
ax=fig.add_axes([0,0,1,1]); ax.set_xlim(0,100); ax.set_ylim(0,100); ax.axis("off")

def box(x,y,w,h,fc,ec=None,lw=1.5,r=0.02):
    ax.add_patch(FancyBboxPatch((x,y),w,h,boxstyle=f"round,pad=0,rounding_size={r*100}",
                mutation_aspect=1,fc=fc,ec=ec or fc,lw=lw))

ax.text(4,94,"Asistente de IA generativa · consulta a los datos",fontsize=25,fontweight="bold",color=TINTA)
ax.text(4,90,"Recupera la evidencia de AquaBosque y responde en lenguaje natural — aterrizado, sin inventar.",
        fontsize=13.5,color=GRIS)

# ---- Columna izquierda: chat ----
# pregunta (usuario)
box(4,79,54,7,"#E8F0FE",ec="#C3D5EF"); ax.text(6.5,82.4,"👤  ¿Por qué La Macarena aparece priorizada?",
        fontsize=15,color=AZUL2,fontweight="bold",va="center")
# respuesta (asistente)
box(4,50,54,26,"#FFFFFF",ec=BORDE); ax.text(6.5,73.2,"🤖  Asistente",fontsize=13,color=VERDE,fontweight="bold")
resp=("La Macarena (Meta) está en nivel Crítico (score 0.51).\n"
      "Pesan una deforestación muy alta (0.97), señal\n"
      "satelital de fuego (0.69) y sensibilidad ambiental\n"
      "máxima (1.00: Serranía protegida). La priorización\n"
      "orienta revisión; no prueba causalidad ni ilegalidad.")
ax.text(6.5,70,resp,fontsize=13,color=TINTA,va="top",linespacing=1.55)
box(6.5,51.5,24,4,"#EAF3EE"); ax.text(8,53.5,"fuente: municipio 50350 · datos abiertos",fontsize=10.5,color=VERDE2,va="center")

# nota inferior izquierda
box(4,40,54,7,"#FFF7ED",ec="#F4B04A"); ax.text(6.5,43.5,"No es un chatbot general: solo responde con la evidencia\nrecuperada del sistema (RAG). Si no está, lo dice.",
        fontsize=12.5,color="#7C4A03",va="center",linespacing=1.4)

# ---- Columna derecha: stack soberano ----
rx=62
ax.text(rx,86,"Cómo funciona · stack soberano",fontsize=16,fontweight="bold",color=TINTA)
pasos=[("Pregunta ciudadana / técnica",AZUL),
       ("🔎  bge-m3 — recupera la evidencia\n(embeddings, 1.024-dim)",VERDE2),
       ("🧠  LLM local — genera la respuesta\nllama3.3:70b · qwen2.5:32b",AZUL2),
       ("Respuesta aterrizada + fuentes",VERDE)]
y=78
for i,(t,c) in enumerate(pasos):
    box(rx,y-5,33,5.4,"#FFFFFF",ec=c,lw=2)
    ax.text(rx+1.6,y-2.3,t,fontsize=12.8,color=TINTA,va="center",fontweight="bold" if i in(1,2) else "normal",linespacing=1.3)
    if i<3: ax.annotate("",xy=(rx+16.5,y-5.8),xytext=(rx+16.5,y-6.6),
                        arrowprops=dict(arrowstyle="-|>",color="#7CA98A",lw=2.5))
    y-=8.6

# caja soberanía (destacada)
box(rx,30,33,12,VERDE); ax.text(rx+16.5,39.5,"SOBERANÍA DE DATOS",fontsize=13,color="#FFFFFF",fontweight="bold",ha="center")
ax.text(rx+16.5,35.5,"Corre en las NVIDIA L40S\ndel Ministerio.\nEl dato no sale del Estado.",
        fontsize=13,color="#FFFFFF",ha="center",va="center",linespacing=1.45)

ax.text(4,33,"Modelos locales:",fontsize=12,color=GRIS,fontweight="bold")
for i,m in enumerate(["llama3.3:70b","qwen2.5:32b","gemma4:31b","bge-m3"]):
    box(4+i*13.5,27.5,12.5,4,"#EAF3EE"); ax.text(4+i*13.5+6.25,29.5,m,fontsize=11.5,color=VERDE,ha="center",va="center")

ax.text(50,3,"IA generativa sobre datos abiertos · infraestructura pública propia · sin exponer el dato ciudadano a terceros",
        fontsize=11,color=GRIS,ha="center")

out=Path(__file__).resolve().parents[1]/"outputs/jurado_2026/assets/24_asistente_rag.png"
fig.savefig(out,facecolor=FONDO,bbox_inches="tight"); print("OK:",out)
