/**
 * Visual Canvas Module for Node-Based Workflow Building
 * Inspired by OpenAI Agent Builder's spatial interface
 */

class VisualCanvas {
    constructor(containerEl, onNodeUpdate) {
        this.container = containerEl;
        this.onNodeUpdate = onNodeUpdate;
        this.nodes = [];
        this.connections = [];
        this.selectedNode = null;
        this.draggingNode = null;
        this.scale = 1;
        this.panX = 0;
        this.panY = 0;
        
        this.init();
    }

    init() {
        this.setupEventListeners();
        this.render();
    }

    setupEventListeners() {
        // Canvas drag and drop
        this.container.addEventListener('dragover', (e) => {
            e.preventDefault();
            this.container.classList.add('drag-over');
        });

        this.container.addEventListener('dragleave', (e) => {
            if (e.target === this.container) {
                this.container.classList.remove('drag-over');
            }
        });

        this.container.addEventListener('drop', (e) => {
            e.preventDefault();
            this.container.classList.remove('drag-over');
            
            const toolType = e.dataTransfer.getData('tool-type');
            if (toolType) {
                // Calculate position relative to canvas
                const rect = this.container.getBoundingClientRect();
                const x = e.clientX - rect.left;
                const y = e.clientY - rect.top;
                
                this.addNodeAtPosition(toolType, x, y);
            }
        });
    }

    addNodeAtPosition(toolType, x, y) {
        const nodeId = `node_${Date.now()}`;
        const node = {
            id: nodeId,
            type: toolType,
            x: x,
            y: y,
            stepData: this.getDefaultStepData(toolType)
        };
        
        this.nodes.push(node);
        
        // Auto-connect to previous node if exists
        if (this.nodes.length > 1) {
            const prevNode = this.nodes[this.nodes.length - 2];
            this.connections.push({
                from: prevNode.id,
                to: nodeId
            });
        }
        
        this.render();
        
        // Callback to update parent component
        if (this.onNodeUpdate) {
            this.onNodeUpdate(this.getStepsFromNodes());
        }
    }

    getDefaultStepData(toolType) {
        const templates = {
            'llm_prompt': {
                step_name: 'AI Processing',
                step_type: 'llm_prompt',
                prompt: 'Transform content...'
            },
            'web_search': {
                step_name: 'Web Search',
                step_type: 'web_search'
            },
            'fact_check': {
                step_name: 'Fact Check',
                step_type: 'fact_check'
            }
        };
        
        return templates[toolType] || templates['llm_prompt'];
    }

    render() {
        // Clear canvas
        const canvasInner = this.container.querySelector('.canvas-inner');
        if (!canvasInner) return;
        
        canvasInner.innerHTML = '';
        
        // Render connections first (so they're behind nodes)
        this.renderConnections(canvasInner);
        
        // Render nodes
        this.nodes.forEach(node => {
            this.renderNode(node, canvasInner);
        });
    }

    renderConnections(container) {
        // Create SVG for connections
        const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
        svg.classList.add('canvas-connections');
        svg.setAttribute('width', '100%');
        svg.setAttribute('height', '100%');
        
        this.connections.forEach(conn => {
            const fromNode = this.nodes.find(n => n.id === conn.from);
            const toNode = this.nodes.find(n => n.id === conn.to);
            
            if (fromNode && toNode) {
                const path = this.createBezierPath(fromNode, toNode);
                svg.appendChild(path);
            }
        });
        
        container.appendChild(svg);
    }

    createBezierPath(fromNode, toNode) {
        const path = document.createElementNS('http://www.w3.org/2000/svg', 'path');
        
        // Start point (bottom of from node)
        const x1 = fromNode.x + 100; // Center of node (approx)
        const y1 = fromNode.y + 120; // Bottom of node
        
        // End point (top of to node)
        const x2 = toNode.x + 100;
        const y2 = toNode.y;
        
        // Control points for smooth curve
        const cy1 = y1 + (y2 - y1) * 0.5;
        const cy2 = y1 + (y2 - y1) * 0.5;
        
        const d = `M ${x1} ${y1} C ${x1} ${cy1}, ${x2} ${cy2}, ${x2} ${y2}`;
        path.setAttribute('d', d);
        path.classList.add('connection-line');
        
        return path;
    }

    renderNode(node, container) {
        const nodeEl = document.createElement('div');
        nodeEl.classList.add('workflow-node');
        nodeEl.style.left = `${node.x}px`;
        nodeEl.style.top = `${node.y}px`;
        nodeEl.setAttribute('data-node-id', node.id);
        
        if (this.selectedNode === node.id) {
            nodeEl.classList.add('node-active');
        }
        
        // Node header
        const header = document.createElement('div');
        header.classList.add('node-header');
        header.innerHTML = `
            <div class="node-icon">${this.getIconForType(node.type)}</div>
            <div class="node-title">${node.stepData.step_name || 'Untitled'}</div>
            <span class="node-badge badge-${this.getBadgeType(node.type)}">${node.type.replace(/_/g, ' ')}</span>
        `;
        
        // Node content
        const content = document.createElement('div');
        content.classList.add('node-content');
        
        if (node.type === 'llm_prompt' && node.stepData.prompt) {
            content.classList.add('sticky-note');
            content.textContent = node.stepData.prompt.substring(0, 60) + (node.stepData.prompt.length > 60 ? '...' : '');
        } else {
            content.textContent = this.getNodeDescription(node);
        }
        
        // Node actions
        const actions = document.createElement('div');
        actions.classList.add('node-actions');
        actions.innerHTML = `
            <button class="node-action-btn" data-action="edit">Edit</button>
            <button class="node-action-btn" data-action="delete">Delete</button>
        `;
        
        nodeEl.appendChild(header);
        nodeEl.appendChild(content);
        nodeEl.appendChild(actions);
        
        // Connectors
        const inputConnector = document.createElement('div');
        inputConnector.classList.add('node-connector', 'input');
        const outputConnector = document.createElement('div');
        outputConnector.classList.add('node-connector', 'output');
        
        nodeEl.appendChild(inputConnector);
        nodeEl.appendChild(outputConnector);
        
        // Event listeners
        this.setupNodeListeners(nodeEl, node);
        
        container.appendChild(nodeEl);
    }

    setupNodeListeners(nodeEl, node) {
        let isDragging = false;
        let startX, startY, initialX, initialY;
        
        nodeEl.addEventListener('mousedown', (e) => {
            if (e.target.classList.contains('node-action-btn')) return;
            
            isDragging = true;
            startX = e.clientX;
            startY = e.clientY;
            initialX = node.x;
            initialY = node.y;
            
            nodeEl.classList.add('dragging');
            this.selectedNode = node.id;
            
            e.preventDefault();
        });
        
        document.addEventListener('mousemove', (e) => {
            if (!isDragging) return;
            
            const dx = e.clientX - startX;
            const dy = e.clientY - startY;
            
            node.x = initialX + dx;
            node.y = initialY + dy;
            
            this.render();
        });
        
        document.addEventListener('mouseup', () => {
            if (isDragging) {
                isDragging = false;
                nodeEl.classList.remove('dragging');
                if (this.onNodeUpdate) {
                    this.onNodeUpdate(this.getStepsFromNodes());
                }
            }
        });
        
        // Action buttons
        nodeEl.querySelector('[data-action="edit"]')?.addEventListener('click', (e) => {
            e.stopPropagation();
            this.editNode(node);
        });
        
        nodeEl.querySelector('[data-action="delete"]')?.addEventListener('click', (e) => {
            e.stopPropagation();
            this.deleteNode(node.id);
        });
    }

    editNode(node) {
        // Trigger edit modal/panel
        if (this.onNodeEdit) {
            this.onNodeEdit(node);
        }
    }

    deleteNode(nodeId) {
        if (!confirm('Delete this step?')) return;
        
        this.nodes = this.nodes.filter(n => n.id !== nodeId);
        this.connections = this.connections.filter(c => c.from !== nodeId && c.to !== nodeId);
        
        this.render();
        
        if (this.onNodeUpdate) {
            this.onNodeUpdate(this.getStepsFromNodes());
        }
    }

    getStepsFromNodes() {
        // Convert nodes back to linear steps array (maintains compatibility)
        return this.nodes.map(node => node.stepData);
    }

    loadSteps(steps) {
        // Convert linear steps to positioned nodes
        this.nodes = steps.map((step, index) => ({
            id: `node_${index}_${Date.now()}`,
            type: step.step_type || 'llm_prompt',
            x: 100,
            y: 100 + (index * 200), // Stack vertically with spacing
            stepData: step
        }));
        
        // Auto-create connections
        this.connections = [];
        for (let i = 0; i < this.nodes.length - 1; i++) {
            this.connections.push({
                from: this.nodes[i].id,
                to: this.nodes[i + 1].id
            });
        }
        
        this.render();
    }

    // Layout and positioning methods
    autoArrange() {
        // Arrange nodes in a clean vertical flow
        const spacing = 200;
        const startX = 150;
        const startY = 100;
        
        this.nodes.forEach((node, index) => {
            node.x = startX;
            node.y = startY + (index * spacing);
        });
        
        this.render();
    }

    fitToView() {
        if (this.nodes.length === 0) return;
        
        // Find bounding box of all nodes
        let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
        
        this.nodes.forEach(node => {
            minX = Math.min(minX, node.x);
            minY = Math.min(minY, node.y);
            maxX = Math.max(maxX, node.x + 300); // Approximate node width
            maxY = Math.max(maxY, node.y + 150); // Approximate node height
        });
        
        // Center the workflow
        const canvasRect = this.container.getBoundingClientRect();
        const workflowWidth = maxX - minX;
        const workflowHeight = maxY - minY;
        
        const offsetX = (canvasRect.width - workflowWidth) / 2 - minX;
        const offsetY = (canvasRect.height - workflowHeight) / 2 - minY;
        
        this.nodes.forEach(node => {
            node.x += offsetX;
            node.y += offsetY;
        });
        
        this.render();
    }

    // Utility methods
    getIconForType(type) {
        const icons = {
            'llm_prompt': '🤖',
            'web_search': '🔍',
            'fact_check': '✅',
            'data_validation': '🔬',
            'podcast_generator': '🎙️',
            'alignment': '🔗',
            'note': '📝'
        };
        return icons[type] || '📝';
    }

    getBadgeType(type) {
        if (type === 'llm_prompt') return 'llm';
        if (type === 'alignment' || type === 'podcast_generator') return 'tool';
        return 'analysis';
    }

    getNodeDescription(node) {
        const descriptions = {
            'web_search': 'Search the web for information',
            'fact_check': 'Verify claims and facts',
            'data_validation': 'Validate data format',
            'podcast_generator': 'Generate audio podcast',
            'alignment': 'Align Excel files',
            'note': 'Add notes and context'
        };
        return descriptions[node.type] || 'Process step';
    }
}

// Export for use in workflow builder
if (typeof window !== 'undefined') {
    window.VisualCanvas = VisualCanvas;
}

