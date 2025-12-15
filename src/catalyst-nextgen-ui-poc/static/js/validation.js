/**
 * Validation System for Workflow Builder
 * Phase 2A Implementation - Design-First Approach
 * 
 * Follows design principles:
 * - Rams: Simple, clear validation rules
 * - Norman: Helpful, actionable error messages
 * - Ive: Smooth animations and micro-interactions
 */

class WorkflowValidator {
    constructor() {
        this.rules = this.initializeRules();
        this.errors = [];
        this.warnings = [];
    }

    initializeRules() {
        return {
            // Workflow-level rules
            workflowName: {
                required: true,
                minLength: 3,
                maxLength: 100,
                message: (value) => {
                    if (!value) return "Workflow name is required. Give your workflow a clear, descriptive name.";
                    if (value.length < 3) return "Workflow name must be at least 3 characters long.";
                    if (value.length > 100) return "Workflow name must be less than 100 characters.";
                    return null;
                }
            },
            
            workflowKey: {
                required: true,
                pattern: /^[a-z0-9_]+$/,
                minLength: 2,
                maxLength: 50,
                message: (value, isEditing) => {
                    if (!value) return "Workflow key is required. Use lowercase letters, numbers, and underscores only.";
                    if (!/^[a-z0-9_]+$/.test(value)) return "Key can only contain lowercase letters, numbers, and underscores.";
                    if (value.length < 2) return "Key must be at least 2 characters long.";
                    if (value.length > 50) return "Key must be less than 50 characters.";
                    return null;
                }
            },
            
            workflowSteps: {
                minSteps: 1,
                message: (steps) => {
                    if (!steps || steps.length === 0) {
                        return "Add at least one step to your workflow. Drag a tool from the toolbox on the right.";
                    }
                    return null;
                }
            },
            
            // Step-level rules
            stepName: {
                required: true,
                minLength: 2,
                maxLength: 100,
                message: (value, stepIndex) => {
                    if (!value) return `Step ${stepIndex + 1} needs a name. Try something like "Extract Topics" or "Summarize Content".`;
                    if (value.length < 2) return "Step name must be at least 2 characters long.";
                    if (value.length > 100) return "Step name is too long. Keep it under 100 characters.";
                    return null;
                }
            },
            
            stepNameUnique: {
                message: (stepName, allSteps, currentIndex) => {
                    const duplicates = allSteps.filter((s, i) => 
                        i !== currentIndex && s.step_name === stepName
                    );
                    if (duplicates.length > 0) {
                        return `Step name "${stepName}" is already used. Give each step a unique name.`;
                    }
                    return null;
                }
            },
            
            stepPrompt: {
                required: true,
                minLength: 10,
                message: (value, stepType, stepIndex) => {
                    if (stepType !== 'llm_prompt') return null; // Only required for LLM steps
                    if (!value) return `Step ${stepIndex + 1} needs a prompt. What should the AI do with the document?`;
                    if (value.length < 10) return "Prompt is too short. Provide clear instructions for the AI (at least 10 characters).";
                    return null;
                }
            },
            
            // Variable rules
            variablesHaveOptions: {
                message: (variables, options) => {
                    const missingOptions = variables.filter(v => !options[v]);
                    if (missingOptions.length > 0) {
                        const varList = missingOptions.map(v => `{${v}}`).join(', ');
                        return `Variables ${varList} need options defined. Click the + button next to each variable to add choices.`;
                    }
                    return null;
                }
            },
            
            // Option rules
            optionConfiguration: {
                message: (optionKey, option) => {
                    const type = option.type || 'select';
                    
                    switch(type) {
                        case 'number':
                            if (option.min === undefined || option.max === undefined) {
                                return `Option "${optionKey}" needs min and max values defined.`;
                            }
                            if (option.min >= option.max) {
                                return `Option "${optionKey}": min value must be less than max value.`;
                            }
                            break;
                        
                        case 'checkbox':
                            if (option.default === undefined) {
                                return `Option "${optionKey}" needs a default value (checked or unchecked).`;
                            }
                            break;
                        
                        case 'textarea':
                            if (!option.rows || option.rows < 1) {
                                return `Option "${optionKey}" needs to specify number of rows (at least 1).`;
                            }
                            break;
                        
                        case 'select':
                            if (!option.choices || option.choices.length === 0) {
                                return `Option "${optionKey}" needs at least one choice. Click "+ Add Choice" to add options.`;
                            }
                            // Check if all choices have values and labels
                            const emptyChoices = option.choices.filter(c => !c.value || !c.label);
                            if (emptyChoices.length > 0) {
                                return `Option "${optionKey}" has choices with missing values or labels. Fill in all fields.`;
                            }
                            break;
                    }
                    
                    return null;
                }
            }
        };
    }

    /**
     * Validate entire workflow
     * Returns { valid: boolean, errors: [], warnings: [] }
     */
    validateWorkflow(workflow) {
        this.errors = [];
        this.warnings = [];
        
        // Validate workflow name
        const nameError = this.rules.workflowName.message(workflow.name);
        if (nameError) this.errors.push({ field: 'name', message: nameError, severity: 'error' });
        
        // Validate workflow key
        const keyError = this.rules.workflowKey.message(workflow.key, workflow.editingExisting);
        if (keyError) this.errors.push({ field: 'key', message: keyError, severity: 'error' });
        
        // Validate steps exist
        const stepsError = this.rules.workflowSteps.message(workflow.steps);
        if (stepsError) this.errors.push({ field: 'steps', message: stepsError, severity: 'error' });
        
        // Validate each step
        if (workflow.steps && workflow.steps.length > 0) {
            workflow.steps.forEach((step, index) => {
                this.validateStep(step, index, workflow.steps);
            });
        }
        
        // Validate variables have options
        const allVariables = this.extractAllVariables(workflow.steps);
        const varsError = this.rules.variablesHaveOptions.message(allVariables, workflow.options || {});
        if (varsError) this.warnings.push({ field: 'variables', message: varsError, severity: 'warning' });
        
        // Validate option configurations
        if (workflow.options) {
            Object.keys(workflow.options).forEach(key => {
                const optError = this.rules.optionConfiguration.message(key, workflow.options[key]);
                if (optError) this.errors.push({ field: `option_${key}`, message: optError, severity: 'error' });
            });
        }
        
        return {
            valid: this.errors.length === 0,
            errors: this.errors,
            warnings: this.warnings,
            hasIssues: this.errors.length > 0 || this.warnings.length > 0
        };
    }

    /**
     * Validate single step
     */
    validateStep(step, index, allSteps) {
        // Validate step name
        const nameError = this.rules.stepName.message(step.step_name, index);
        if (nameError) {
            this.errors.push({ 
                field: `step_${index}_name`, 
                message: nameError, 
                severity: 'error',
                stepIndex: index 
            });
        }
        
        // Check step name uniqueness
        if (step.step_name) {
            const uniqueError = this.rules.stepNameUnique.message(step.step_name, allSteps, index);
            if (uniqueError) {
                this.warnings.push({ 
                    field: `step_${index}_name_unique`, 
                    message: uniqueError, 
                    severity: 'warning',
                    stepIndex: index 
                });
            }
        }
        
        // Validate prompt for LLM steps
        const promptError = this.rules.stepPrompt.message(step.prompt, step.step_type, index);
        if (promptError) {
            this.errors.push({ 
                field: `step_${index}_prompt`, 
                message: promptError, 
                severity: 'error',
                stepIndex: index 
            });
        }
    }

    /**
     * Extract all variables from workflow steps
     */
    extractAllVariables(steps) {
        const variables = new Set();
        const builtInVariables = ['document_content', 'previous_output'];
        
        if (!steps) return [];
        
        steps.forEach(step => {
            if (step.prompt) {
                const matches = step.prompt.match(/\{([a-zA-Z_][a-zA-Z0-9_]*)\}/g);
                if (matches) {
                    matches.forEach(match => {
                        const varName = match.replace(/[{}]/g, '');
                        if (!builtInVariables.includes(varName)) {
                            variables.add(varName);
                        }
                    });
                }
            }
        });
        
        return Array.from(variables);
    }

    /**
     * Validate single field (for real-time validation)
     * Returns error message or null
     */
    validateField(fieldName, value, context = {}) {
        switch(fieldName) {
            case 'workflowName':
                return this.rules.workflowName.message(value);
            
            case 'workflowKey':
                return this.rules.workflowKey.message(value, context.isEditing);
            
            case 'stepName':
                return this.rules.stepName.message(value, context.stepIndex || 0);
            
            case 'stepPrompt':
                return this.rules.stepPrompt.message(value, context.stepType, context.stepIndex || 0);
            
            default:
                return null;
        }
    }
}

// Export for use in workflow builder
if (typeof window !== 'undefined') {
    window.WorkflowValidator = WorkflowValidator;
}


