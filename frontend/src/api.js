// api.js - all calls to the FastAPI backend live here.
// Components import these functions instead of writing axios calls directly.
import axios from "axios";

// FastAPI runs on port 8000 (Vite runs on 5173).
const API = axios.create({ baseURL: "http://localhost:8000" });

// ---- reads ----
export const getNodes   = () => API.get("/nodes").then(r => r.data);
export const getEdges   = () => API.get("/edges").then(r => r.data);
export const getHealth  = () => API.get("/health").then(r => r.data);
export const getAlerts  = () => API.get("/alerts").then(r => r.data);
export const getAudit   = () => API.get("/audit").then(r => r.data);
export const getUsers   = () => API.get("/users").then(r => r.data);

// ---- actions ----
export const runCascade = (nodeId, actorId = "U-MEERA") =>
  API.post("/cascade", { node_id: nodeId, actor_id: actorId }).then(r => r.data);

export const review = (nodeId, action, actorId = "U-MEERA", actorRole = "HOD",
                       newTitle = null, newContent = null) =>
  API.post("/review", {
    node_id: nodeId, action, actor_id: actorId, actor_role: actorRole,
    new_title: newTitle, new_content: newContent,
  }).then(r => r.data);

export const resetDemo = () => API.post("/reset").then(r => r.data);