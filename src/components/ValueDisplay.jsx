import React, { useEffect, useRef, useState } from 'react';

export default function ValueDisplay({ value, text, className = '' }) {
  const prevValue = useRef(value);
  const [flashClass, setFlashClass] = useState('');

  useEffect(() => {
    if (prevValue.current !== undefined && value !== prevValue.current) {
      if (value > prevValue.current) {
        setFlashClass(''); // force reflow
        setTimeout(() => setFlashClass('flash-up'), 10);
      } else if (value < prevValue.current) {
        setFlashClass('');
        setTimeout(() => setFlashClass('flash-down'), 10);
      }
      
      const timer = setTimeout(() => {
        setFlashClass('');
      }, 1000);
      
      return () => clearTimeout(timer);
    }
    prevValue.current = value;
  }, [value]);

  return (
    <span className={`${className} ${flashClass}`}>
      {text}
    </span>
  );
}
