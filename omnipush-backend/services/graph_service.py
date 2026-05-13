import os
import json
import networkx as nx
import plotly.graph_objects as go
import plotly.offline as pyo
from openai import AsyncOpenAI
from typing import Dict, Any, List, Tuple
from config.prompts import Prompts
import json_repair



class GraphService:
    def __init__(self):
        self.openai_client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    async def generate_knowledge_graph(
        self, city: str, research_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate a knowledge graph for the city based on research data"""

        # Extract entities and relationships using OpenAI
        graph_data = await self._extract_graph_entities(city, research_data)

        # Create NetworkX graph
        G = nx.Graph()

        # Add nodes and edges
        for node in graph_data["nodes"]:
            G.add_node(node["id"], **node)

        for edge in graph_data["edges"]:
            G.add_edge(edge["source"], edge["target"], **edge)

        # Generate layout
        pos = nx.spring_layout(G, k=3, iterations=50)

        # Create Plotly traces
        traces, layout = self._create_plotly_visualization(G, pos)

        return {"traces": traces, "layout": layout, "graph_data": graph_data}

    async def _extract_graph_entities(
        self, city: str, research_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Extract entities and relationships from research data using OpenAI"""

        combined_research = f"""
        OpenAI Analysis: {research_data.get('openai_analysis', '')}
        Perplexity Research: {research_data.get('perplexity_research', '')}
        """

        try:
            response = await self.openai_client.chat.completions.create(
                model="gpt-4.1",
                messages=Prompts.get_knowledge_graph_messages(city, combined_research),
                # max_tokens=1500,
            )

            content = response.choices[0].message.content

            # Clean the response to extract JSON
            # if "```json" in content:
            #     content = content.split("```json")[1].split("```")[0]
            # elif "```" in content:
            #     content = content.split("```")[1].split("```")[0]

            return json_repair.loads(content.strip())

        except Exception as e:
            # Fallback basic graph structure
            return self._create_fallback_graph(city)

    def _create_fallback_graph(self, city: str) -> Dict[str, Any]:
        """Create a basic fallback graph structure"""
        return {
            "nodes": [
                {
                    "id": "city",
                    "label": city,
                    "type": "city",
                    "description": f"The city of {city}",
                    "size": 20,
                },
                {
                    "id": "government",
                    "label": "Government",
                    "type": "government",
                    "description": "Local government",
                    "size": 15,
                },
                {
                    "id": "economy",
                    "label": "Economy",
                    "type": "economy",
                    "description": "Economic sector",
                    "size": 15,
                },
                {
                    "id": "culture",
                    "label": "Culture",
                    "type": "culture",
                    "description": "Cultural aspects",
                    "size": 12,
                },
                {
                    "id": "demographics",
                    "label": "Demographics",
                    "type": "demographics",
                    "description": "Population data",
                    "size": 12,
                },
            ],
            "edges": [
                {
                    "source": "city",
                    "target": "government",
                    "relationship": "governed_by",
                    "description": "Administrative relationship",
                },
                {
                    "source": "city",
                    "target": "economy",
                    "relationship": "has_economy",
                    "description": "Economic relationship",
                },
                {
                    "source": "city",
                    "target": "culture",
                    "relationship": "has_culture",
                    "description": "Cultural relationship",
                },
                {
                    "source": "city",
                    "target": "demographics",
                    "relationship": "has_population",
                    "description": "Demographic relationship",
                },
            ],
        }

    def _create_plotly_visualization(self, G: nx.Graph, pos: Dict) -> Tuple[List, Dict]:
        """Create Plotly visualization from NetworkX graph"""

        # Extract node positions
        node_x = [pos[node][0] for node in G.nodes()]
        node_y = [pos[node][1] for node in G.nodes()]

        # Node information
        node_text = []
        node_sizes = []
        node_colors = []
        node_info = []

        color_map = {
            "city": "red",
            "government": "blue",
            "economy": "green",
            "culture": "purple",
            "demographics": "orange",
            "infrastructure": "brown",
            "education": "pink",
            "healthcare": "cyan",
            "tourism": "yellow",
            "issues": "gray",
        }

        for node in G.nodes():
            node_data = G.nodes[node]
            node_text.append(node_data.get("label", node))
            node_sizes.append(node_data.get("size", 10))
            node_type = node_data.get("type", "default")
            node_colors.append(color_map.get(node_type, "lightblue"))
            node_info.append(node_data.get("description", "No description available"))

        # Create edges
        edge_x = []
        edge_y = []

        for edge in G.edges():
            x0, y0 = pos[edge[0]]
            x1, y1 = pos[edge[1]]
            edge_x.extend([x0, x1, None])
            edge_y.extend([y0, y1, None])

        # Create traces
        edge_trace = go.Scatter(
            x=edge_x,
            y=edge_y,
            line=dict(width=2, color="lightgray"),
            hoverinfo="none",
            mode="lines",
        )

        node_trace = go.Scatter(
            x=node_x,
            y=node_y,
            mode="markers+text",
            hoverinfo="text",
            text=node_text,
            textposition="middle center",
            hovertext=node_info,
            customdata=node_info,
            marker=dict(
                size=node_sizes, color=node_colors, line=dict(width=2, color="white")
            ),
        )

        traces = [edge_trace, node_trace]

        layout = go.Layout(
            title=dict(text="Knowledge Graph", font=dict(size=16)),
            showlegend=False,
            hovermode="closest",
            margin=dict(b=20, l=5, r=5, t=40),
            annotations=[
                dict(
                    text="Click on nodes to see details",
                    showarrow=False,
                    xref="paper",
                    yref="paper",
                    x=0.005,
                    y=-0.002,
                    xanchor="left",
                    yanchor="bottom",
                    font=dict(color="#888", size=12),
                )
            ],
            xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            plot_bgcolor="white",
        )

        # Return JSON-serializable structures for FastAPI/JSONResponse
        traces_json = [t.to_plotly_json() for t in traces]
        layout_json = layout.to_plotly_json()

        return traces_json, layout_json
