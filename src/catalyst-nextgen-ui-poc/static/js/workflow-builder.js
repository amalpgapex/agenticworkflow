/**
 * Workflow Builder - Main Component
 * Modular Alpine.js component for visual workflow creation
 */

function workflowBuilder() {
    return {
        // ============================================
        // STATE - Workflow Data
        // ============================================
        workflow: {
            name: '',
            key: '',
            description: '',
            canvas_type: 'text_editor',
            input_file_types: ['docx', 'txt', 'md'],
            steps: [],
            options: {}
        },
        
        // ============================================
        // STATE - UI
        // ============================================
        activeStep: null,
        editingExisting: false,
        sortable: null,
        showOptionsManager: true,
        showVariablesPanel: true,
        showTemplates: false,
        showQuickGuide: false,
        
        // ============================================
        // STATE - Validation
        // ============================================
        validator: null,
        validationResult: {
            valid: true,
            errors: [],
            warnings: [],
            hasIssues: false
        },
        fieldValidations: {},
        
        // ============================================
        // STATE - Templates
        // ============================================
        templates: [],
        filteredTemplates: [],
        templateSearch: '',
        
        // ============================================
        // STATE - Drag & Drop
        // ============================================
        isDraggingFromToolbox: false,
        dropLock: false,
        
        // ============================================
        // STATE - View Mode
        // ============================================
        canvasViewMode: 'list', // 'list' or 'visual'
        visualCanvas: null,

        // ============================================
        // LIFECYCLE - Initialization
        // ============================================
        async init() {
            await this.initializeValidator();
            await this.loadTemplates();
            await this.checkForEdit();
            this.initDragAndDrop();
            this.initVisualCanvas();
            this.setupKeyboardShortcuts();
        },
        
        initVisualCanvas() {
            // Initialize visual canvas if available
            this.$watch('canvasViewMode', (newMode) => {
                if (newMode === 'visual') {
                    this.$nextTick(() => {
                        const canvasEl = document.getElementById('visual-canvas');
                        if (canvasEl && typeof VisualCanvas !== 'undefined') {
                            this.visualCanvas = new VisualCanvas(canvasEl, (steps) => {
                                this.workflow.steps = steps;
                                this.runFullValidation();
                            });
                            
                            // Load existing steps into visual canvas
                            if (this.workflow.steps.length > 0) {
                                this.visualCanvas.loadSteps(this.workflow.steps);
                            }
                        }
                    });
                }
            });
        },

        async initializeValidator() {
            if (typeof WorkflowValidator !== 'undefined') {
                this.validator = new WorkflowValidator();
            }
        },

        async checkForEdit() {
            const urlParams = new URLSearchParams(window.location.search);
            const editKey = urlParams.get('edit');
            if (editKey) {
                await this.loadWorkflow(editKey);
            }
        },

        setupKeyboardShortcuts() {
            document.addEventListener('keydown', (e) => {
                if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA' || e.target.isContentEditable) {
                    return;
                }
                
                if (e.key === 'Escape') {
                    if (this.showTemplates) {
                        this.showTemplates = false;
                    } else if (this.activeStep !== null) {
                        this.activeStep = null;
                    }
                    e.preventDefault();
                }
            });
        },

        // ============================================
        // MODULE - Workflow Loading/Saving
        // ============================================
        async loadWorkflow(key) {
            try {
                const response = await fetch(`/api/transformation/${key}`);
                const data = await response.json();
                this.workflow = {
                    name: data.name,
                    key: data.key,
                    description: data.description || '',
                    canvas_type: data.canvas_type || 'text_editor',
                    input_file_types: data.input_file_types || ['docx'],
                    steps: data.steps || [],
                    options: data.options || {}
                };
                this.editingExisting = true;
                
                this.$nextTick(() => this.runFullValidation());
            } catch (error) {
                console.error('Error loading workflow:', error);
                alert('Error loading workflow');
            }
        },

        async saveWorkflow() {
            const validation = this.validateWorkflowComplete();
            
            if (!validation.valid) {
                this.validationResult = validation;
                alert(`Cannot save: ${validation.errors.length} error${validation.errors.length > 1 ? 's' : ''} found. Please fix the issues highlighted above.`);
                window.scrollTo({ top: 0, behavior: 'smooth' });
                return;
            }
            
            if (validation.warnings.length > 0) {
                const proceed = confirm(`Found ${validation.warnings.length} suggestion${validation.warnings.length > 1 ? 's' : ''}. Do you want to save anyway?`);
                if (!proceed) return;
            }

            try {
                const method = this.editingExisting ? 'PUT' : 'POST';
                const url = this.editingExisting 
                    ? `/api/transformation/${this.workflow.key}` 
                    : '/api/transformation';

                const response = await fetch(url, {
                    method,
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(this.workflow)
                });

                const data = await response.json();
                
                if (data.success) {
                    alert('✅ Direction saved successfully!');
                    window.location.href = '/studio?view=manager';
                } else {
                    alert('Error: ' + (data.error || 'Could not save direction'));
                }
            } catch (error) {
                console.error('Error saving workflow:', error);
                alert('Error saving workflow');
            }
        },

        async exportWorkflow() {
            if (!this.workflow.key) {
                alert('Please save the workflow first before exporting.');
                return;
            }
            
            try {
                const response = await fetch(`/api/transformation/${this.workflow.key}/export`);
                const blob = await response.blob();
                
                const url = URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = `${this.workflow.key}.json`;
                a.click();
                URL.revokeObjectURL(url);
                
                this.showNotification('✅ Workflow exported successfully!', 'success');
            } catch (error) {
                console.error('Export error:', error);
                alert('Error exporting workflow');
            }
        },

        async importWorkflow(event) {
            const file = event.target.files[0];
            if (!file) return;
            
            try {
                const text = await file.text();
                const data = JSON.parse(text);
                
                const response = await fetch('/api/transformation/import', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(data)
                });
                
                const result = await response.json();
                
                if (result.success) {
                    this.showNotification(`✅ Workflow "${result.name}" imported successfully!`, 'success');
                    setTimeout(() => {
                        window.location.href = `/workflow-builder?edit=${result.key}`;
                    }, 1500);
                } else {
                    alert(`Import failed: ${result.error}`);
                }
            } catch (error) {
                console.error('Import error:', error);
                alert('Error importing workflow. Please check the file format.');
            }
            
            event.target.value = '';
        },

        previewWorkflow() {
            alert('Preview mode coming soon! This will show you how your workflow will execute.');
        },

        // ============================================
        // MODULE - Validation
        // ============================================
        validateField(fieldName, value, context = {}) {
            if (!this.validator) return;
            
            const error = this.validator.validateField(fieldName, value, {
                ...context,
                isEditing: this.editingExisting
            });
            
            const fieldMap = {
                'workflowName': 'name',
                'workflowKey': 'key'
            };
            
            const mappedField = fieldMap[fieldName] || fieldName;
            
            if (error) {
                this.fieldValidations[mappedField] = {
                    field: mappedField,
                    message: error,
                    severity: 'error'
                };
            } else {
                delete this.fieldValidations[mappedField];
            }
            
            this.runFullValidation();
        },

        validateWorkflowComplete() {
            if (!this.validator) {
                return { valid: true, errors: [], warnings: [], hasIssues: false };
            }
            return this.validator.validateWorkflow(this.workflow);
        },

        runFullValidation() {
            this.validationResult = this.validateWorkflowComplete();
        },

        getFieldValidation(field) {
            return this.fieldValidations[field] || null;
        },

        // ============================================
        // MODULE - Steps Management
        // ============================================
        toggleStep(index) {
            if (this.activeStep === index) {
                this.activeStep = null;
            } else {
                this.activeStep = index;
                this.$nextTick(() => this.scrollToStep(index));
            }
        },

        selectStep(index) {
            this.toggleStep(index);
        },

        editStep(index) {
            this.activeStep = index;
            this.$nextTick(() => this.scrollToStep(index));
        },

        deleteStep(index) {
            if (confirm('Delete this step?')) {
                this.workflow.steps.splice(index, 1);
                this.activeStep = null;
                this.runFullValidation();
            }
        },

        addStepFromTool(toolType) {
            const stepTemplates = {
                llm_prompt: {
                    step_name: 'New AI Step',
                    step_type: 'llm_prompt',
                    prompt: 'Enter your prompt here...'
                },
                web_search: {
                    step_name: 'Web Search',
                    step_type: 'web_search',
                    parameters: { search_query: '{topic}' }
                },
                fact_check: {
                    step_name: 'Fact Check',
                    step_type: 'fact_check',
                    parameters: {}
                },
                data_validation: {
                    step_name: 'Validate Data',
                    step_type: 'data_validation',
                    parameters: { validation_type: 'all' }
                },
                podcast_generator: {
                    step_name: 'Generate Podcast',
                    step_type: 'podcast_generator',
                    parameters: { voice: 'alloy' }
                },
                alignment: {
                    step_name: 'Align Files',
                    step_type: 'alignment',
                    parameters: {}
                }
            };

            const newStep = stepTemplates[toolType] || stepTemplates.llm_prompt;
            this.workflow.steps.push(newStep);
            this.activeStep = this.workflow.steps.length - 1;
            
            this.$nextTick(() => this.scrollToStep(this.activeStep));
            this.runFullValidation();
        },

        getStepPreview(step) {
            const type = step.step_type || 'llm_prompt';
            const typeName = type.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
            let preview = typeName;
            
            if (type === 'llm_prompt' && step.prompt) {
                const varCount = (step.prompt.match(/\{[a-zA-Z_][a-zA-Z0-9_]*\}/g) || []).length;
                preview += ` • ${varCount} variable${varCount !== 1 ? 's' : ''}`;
                preview += ` • ${step.prompt.length} chars`;
            }
            
            const isConfigured = step.step_name && 
                               (type !== 'llm_prompt' || (step.prompt && step.prompt.length >= 10));
            
            preview += isConfigured ? ' • Configured ✓' : ' • Needs configuration';
            return preview;
        },

        scrollToStep(index) {
            const stepElement = document.querySelector(`[data-index="${index}"]`);
            if (stepElement) {
                stepElement.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
            }
        },

        // ============================================
        // MODULE - Variables Management
        // ============================================
        detectVariablesInPrompt(stepIndex) {
            const step = this.workflow.steps[stepIndex];
            if (!step || step.step_type !== 'llm_prompt') return;
            
            const variables = this.getDetectedVariables(stepIndex);
            step.template_variables = variables;
            this.runFullValidation();
        },

        getDetectedVariables(stepIndex) {
            const step = this.workflow.steps[stepIndex];
            if (!step || !step.prompt) return [];
            
            const matches = step.prompt.match(/\{([a-zA-Z_][a-zA-Z0-9_]*)\}/g);
            if (!matches) return [];
            
            const builtInVariables = ['document_content', 'previous_output'];
            const variables = matches
                .map(m => m.replace(/[{}]/g, ''))
                .filter((v, i, arr) => arr.indexOf(v) === i)
                .filter(v => !builtInVariables.includes(v));
            
            return variables;
        },

        getAllWorkflowVariables() {
            const variableUsage = new Map();
            const builtInVariables = ['document_content', 'previous_output', 'fact_check_results', 
                                      'labeled_documents', 'current_state', 'step_history',
                                      'secondary_document_content'];
            
            this.workflow.steps.forEach((step, stepIndex) => {
                if (step.prompt) {
                    const matches = step.prompt.match(/\{([a-zA-Z_][a-zA-Z0-9_]*)\}/g);
                    if (matches) {
                        matches.forEach(match => {
                            const varName = match.replace(/[{}]/g, '');
                            if (!builtInVariables.includes(varName) && !varName.includes('.')) {
                                if (!variableUsage.has(varName)) {
                                    variableUsage.set(varName, []);
                                }
                                if (!variableUsage.get(varName).includes(stepIndex)) {
                                    variableUsage.get(varName).push(stepIndex);
                                }
                            }
                        });
                    }
                }
            });
            
            return Array.from(variableUsage.entries()).map(([name, usage]) => ({
                name: name,
                usage: usage,
                hasOption: !!this.workflow.options[name]
            })).sort((a, b) => {
                if (a.hasOption !== b.hasOption) return a.hasOption ? 1 : -1;
                if (a.usage.length !== b.usage.length) return b.usage.length - a.usage.length;
                return a.name.localeCompare(b.name);
            });
        },

        // ============================================
        // MODULE - Options Management
        // ============================================
        addOptionForVariable(variableName) {
            if (!this.workflow.options) {
                this.workflow.options = {};
            }
            
            this.workflow.options[variableName] = {
                type: 'select',
                label: this.toTitleCase(variableName),
                description: `Select a value for ${variableName}`,
                choices: [
                    { value: 'option1', label: 'Option 1' },
                    { value: 'option2', label: 'Option 2' }
                ]
            };
            
            this.showOptionsManager = true;
        },

        handleOptionTypeChange(optionKey, newType) {
            const option = this.workflow.options[optionKey];
            if (!option) return;
            
            switch(newType) {
                case 'number':
                    option.min = option.min || 0;
                    option.max = option.max || 100;
                    option.step = option.step || 1;
                    option.default = option.default || 0;
                    delete option.choices;
                    break;
                case 'checkbox':
                    option.default = option.default !== undefined ? option.default : false;
                    delete option.choices;
                    break;
                case 'text':
                    option.placeholder = option.placeholder || 'Enter text...';
                    option.maxLength = option.maxLength || 100;
                    option.default = option.default || '';
                    delete option.choices;
                    break;
                case 'textarea':
                    option.rows = option.rows || 4;
                    option.placeholder = option.placeholder || 'Enter text...';
                    option.maxLength = option.maxLength || 500;
                    delete option.choices;
                    break;
                case 'select':
                    if (!option.choices || option.choices.length === 0) {
                        option.choices = [
                            { value: 'option1', label: 'Option 1' },
                            { value: 'option2', label: 'Option 2' }
                        ];
                    }
                    break;
            }
            
            this.runFullValidation();
        },

        addChoiceToOption(optionKey) {
            if (!this.workflow.options[optionKey]) return;
            this.workflow.options[optionKey].choices.push({ value: '', label: '' });
        },

        removeChoiceFromOption(optionKey, choiceIndex) {
            if (!this.workflow.options[optionKey]) return;
            this.workflow.options[optionKey].choices.splice(choiceIndex, 1);
        },

        deleteOption(optionKey) {
            if (confirm(`Delete option for {${optionKey}}?`)) {
                delete this.workflow.options[optionKey];
                this.runFullValidation();
            }
        },

        getOptionTypeLabel(option) {
            if (!option) return '';
            
            const type = option.type || 'select';
            const typeLabels = {
                'select': 'Dropdown',
                'number': 'Number Input',
                'checkbox': 'Checkbox',
                'text': 'Text Input',
                'textarea': 'Text Area'
            };
            
            return typeLabels[type] || type;
        },

        scrollToOption(varName) {
            this.showOptionsManager = true;
            
            this.$nextTick(() => {
                const optionElement = document.querySelector(`[data-option-key="${varName}"]`);
                if (optionElement) {
                    optionElement.scrollIntoView({ behavior: 'smooth', block: 'center' });
                    optionElement.style.background = 'rgba(59, 130, 246, 0.1)';
                    setTimeout(() => { optionElement.style.background = ''; }, 1000);
                }
            });
        },

        // ============================================
        // MODULE - Templates
        // ============================================
        async loadTemplates() {
            try {
                const response = await fetch('/step_templates.json');
                const data = await response.json();
                this.templates = data.templates || [];
                this.filteredTemplates = this.templates;
            } catch (error) {
                console.error('Error loading templates:', error);
                this.templates = [];
                this.filteredTemplates = [];
            }
        },

        filterTemplates() {
            if (!this.templateSearch) {
                this.filteredTemplates = this.templates;
                return;
            }
            
            const search = this.templateSearch.toLowerCase();
            this.filteredTemplates = this.templates.filter(t => 
                t.name.toLowerCase().includes(search) ||
                t.description.toLowerCase().includes(search) ||
                t.category.toLowerCase().includes(search)
            );
        },

        insertTemplate(template) {
            const newStep = JSON.parse(JSON.stringify(template.step));
            this.workflow.steps.push(newStep);
            this.activeStep = this.workflow.steps.length - 1;
            
            this.showTemplates = false;
            this.templateSearch = '';
            
            this.$nextTick(() => this.scrollToStep(this.activeStep));
            this.runFullValidation();
        },

        // ============================================
        // MODULE - Drag & Drop
        // ============================================
        initDragAndDrop() {
            const container = document.getElementById('steps-container');
            
            // Initialize SortableJS for step reordering
            this.sortable = new Sortable(container, {
                animation: 300,
                handle: '.step-drag-handle',
                ghostClass: 'sortable-ghost',
                dragClass: 'sortable-drag',
                easing: 'cubic-bezier(0.4, 0, 0.2, 1)',
                onStart: () => {
                    this.activeStep = null;
                },
                onEnd: (evt) => {
                    const item = this.workflow.steps.splice(evt.oldIndex, 1)[0];
                    this.workflow.steps.splice(evt.newIndex, 0, item);
                    this.runFullValidation();
                }
            });

            // Setup toolbox drag
            const toolItems = document.querySelectorAll('.tool-item');
            toolItems.forEach(item => {
                item.addEventListener('dragstart', (e) => {
                    this.isDraggingFromToolbox = true;
                    const toolType = e.target.closest('.tool-item').dataset.tool;
                    e.dataTransfer.setData('tool-type', toolType);
                });
                
                item.addEventListener('dragend', () => {
                    this.isDraggingFromToolbox = false;
                    this.dropLock = false;
                });
            });

            // Setup drop zone
            const canvas = document.querySelector('.workflow-canvas');
            
            canvas.addEventListener('dragover', (e) => {
                if (this.isDraggingFromToolbox) {
                    e.preventDefault();
                }
            });

            canvas.addEventListener('drop', (e) => {
                if (!this.isDraggingFromToolbox || this.dropLock) {
                    return;
                }
                
                e.preventDefault();
                e.stopPropagation();
                
                this.dropLock = true;
                const toolType = e.dataTransfer.getData('tool-type');
                if (toolType) {
                    this.addStepFromTool(toolType);
                }
                
                this.isDraggingFromToolbox = false;
                setTimeout(() => { this.dropLock = false; }, 200);
            });
        },

        // ============================================
        // MODULE - Visual Canvas Controls
        // ============================================
        zoomIn() {
            if (this.visualCanvas) {
                this.visualCanvas.scale = Math.min(this.visualCanvas.scale + 0.1, 2);
                this.visualCanvas.render();
            }
        },
        
        zoomOut() {
            if (this.visualCanvas) {
                this.visualCanvas.scale = Math.max(this.visualCanvas.scale - 0.1, 0.5);
                this.visualCanvas.render();
            }
        },
        
        fitToView() {
            if (this.visualCanvas) {
                this.visualCanvas.fitToView();
            }
        },
        
        autoArrange() {
            if (this.visualCanvas) {
                this.visualCanvas.autoArrange();
                this.showNotification('Workflow arranged automatically', 'success');
            }
        },
        
        // ============================================
        // UTILITIES
        // ============================================
        toTitleCase(str) {
            return str
                .split('_')
                .map(word => word.charAt(0).toUpperCase() + word.slice(1))
                .join(' ');
        },

        showNotification(message, type = 'info') {
            const color = type === 'success' ? 'bg-green-500' : 'bg-blue-500';
            const notification = document.createElement('div');
            notification.className = `fixed top-4 right-4 ${color} text-white px-6 py-3 rounded-lg shadow-lg z-50`;
            notification.textContent = message;
            notification.style.animation = 'slideInRight 300ms ease-out';
            
            document.body.appendChild(notification);
            
            setTimeout(() => {
                notification.style.animation = 'slideOutRight 300ms ease-out';
                setTimeout(() => notification.remove(), 300);
            }, 3000);
        }
    };
}

