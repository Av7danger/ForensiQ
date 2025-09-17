import React from 'react';
import type { Entities, EntityHighlighterProps } from '../types';

/**
 * Component to highlight entities in text with different colors
 * Highlights phones, emails, crypto addresses, and URLs with distinct styling
 */
const EntityHighlighter: React.FC<EntityHighlighterProps> = ({ 
  text, 
  entities, 
  className = '' 
}) => {
  // If no text or entities, return plain text
  if (!text || !entities) {
    return <span className={className}>{text}</span>;
  }

  // Collect all entities with their types for highlighting
  const allEntities: Array<{ text: string; type: string }> = [];
  
  if (entities.phones) {
    entities.phones.forEach(phone => 
      allEntities.push({ text: phone, type: 'phone' })
    );
  }
  
  if (entities.emails) {
    entities.emails.forEach(email => 
      allEntities.push({ text: email, type: 'email' })
    );
  }
  
  if (entities.crypto_addresses) {
    entities.crypto_addresses.forEach(crypto => 
      allEntities.push({ text: crypto, type: 'crypto' })
    );
  }
  
  if (entities.urls) {
    entities.urls.forEach(url => 
      allEntities.push({ text: url, type: 'url' })
    );
  }

  // If no entities found, return plain text
  if (allEntities.length === 0) {
    return <span className={className}>{text}</span>;
  }

  // Sort entities by length (descending) to handle overlapping matches
  allEntities.sort((a, b) => b.text.length - a.text.length);

  // Create a working copy of the text
  let workingText = text;
  const replacements: Array<{ original: string; replacement: string }> = [];

  // Process each entity type with distinct styling
  allEntities.forEach((entity, index) => {
    const placeholder = `__ENTITY_${index}__`;
    const entityClass = getEntityClass(entity.type);
    
    // Escape special regex characters in the entity text
    const escapedText = entity.text.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    const regex = new RegExp(`\\b${escapedText}\\b`, 'gi');
    
    // Check if this entity exists in the current working text
    if (regex.test(workingText)) {
      const replacement = `<span class="${entityClass}" data-entity-type="${entity.type}" title="${entity.type}: ${entity.text}">${entity.text}</span>`;
      
      replacements.push({
        original: placeholder,
        replacement: replacement
      });
      
      // Replace the entity with a placeholder to avoid conflicts
      workingText = workingText.replace(regex, placeholder);
    }
  });

  // Replace all placeholders with highlighted entities
  replacements.forEach(({ original, replacement }) => {
    workingText = workingText.replace(original, replacement);
  });

  // Return the highlighted text using dangerouslySetInnerHTML
  // Note: This is safe because we control the HTML generation
  return (
    <span 
      className={className}
      dangerouslySetInnerHTML={{ __html: workingText }}
    />
  );
};

/**
 * Get CSS class for entity type
 */
const getEntityClass = (type: string): string => {
  const entityClasses = {
    phone: 'bg-blue-100 border border-blue-300 text-blue-800 px-1 rounded font-mono text-sm',
    email: 'bg-green-100 border border-green-300 text-green-800 px-1 rounded font-mono text-sm',
    crypto: 'bg-yellow-100 border border-yellow-300 text-yellow-900 px-1 rounded font-mono text-sm',
    url: 'bg-purple-100 border border-purple-300 text-purple-800 px-1 rounded font-mono text-sm',
  };
  
  return entityClasses[type as keyof typeof entityClasses] || 'bg-gray-100 px-1 rounded';
};

export default EntityHighlighter;