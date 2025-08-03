from fastapi import APIRouter, Request, HTTPException
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.agents import tool, AgentExecutor, create_openai_tools_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
import os

router = APIRouter()

@tool
def add_task(task_name: str, start_time: str, end_time: str):
    """Gunakan alat ini untuk menambahkan tugas baru ke kalender dan database."""
    print(f"--- AGENT ACTION: Menambahkan tugas '{task_name}' ---")
    # TODO: Panggil logika dari create_calendar_event.py di sini.
    return f"Tugas '{task_name}' berhasil ditambahkan."

@tool
def delete_task(task_name: str):
    """Gunakan alat ini untuk menghapus tugas dari kalender dan database berdasarkan namanya."""
    print(f"--- AGENT ACTION: Menghapus tugas '{task_name}' ---")
    # TODO: Panggil logika dari delete_task.py di sini. 
    return f"Tugas '{task_name}' berhasil dihapus."

@tool
def update_task(task_name: str, new_details: dict):
    """Gunakan alat ini untuk mengubah detail tugas yang sudah ada."""
    print(f"--- AGENT ACTION: Mengubah tugas '{task_name}' ---")
    # TODO: Panggil logika dari update_task.py di sini.
    return f"Tugas '{task_name}' berhasil diubah."

@router.post("/.netlify/functions/agent_handler")
async def handle_agent_query(request: Request):
    body = await request.json()
    query = body.get("query")
    
    if not query:
        raise HTTPException(status_code=400, detail="Query tidak boleh kosong.")
    
    try:
        if not os.environ.get("GOOGLE_API_KEY"):
            raise ValueError("GOOGLE_API_KEY environment variable not set.")

        llm = ChatGoogleGenerativeAI(
            model="gemini-pro", 
            temperature=0,
            convert_system_message_to_human=True
        )
        tools = [add_task, delete_task, update_task]
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", "You are a helpful assistant named Chronos that manages a user's schedule. You can add, update, and delete tasks. You must use the tools provided to fulfill the user's request."),
            ("user", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad"),
        ])
        
        agent = create_openai_tools_agent(llm, tools, prompt)
        agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True)
        
        result = await agent_executor.ainvoke({"input": query})
        return {"response": result.get("output", "Tugas selesai diproses.")}
    except Exception as e:
        print(f"ERROR during agent execution or initialization: {e}")
        raise HTTPException(status_code=500, detail=f"Agent Error: {e}")