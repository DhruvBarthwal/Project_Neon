import React from 'react'

const Metrics = () => {
  return (
    <div className='h-1/4 w-full'>
        <div className='mx-8'>
            <h1 className='font-semibold text-3xl'>Dashboard</h1>
        </div>
        <div className='flex bg-red-500 h-full gap-5 py-2 px-8'>
            <div className='bg-white border border-white rounded-2xl w-1/6 h-3/4'></div>
            <div className='bg-white border border-white rounded-2xl w-1/6 h-3/4'></div>
            <div className='bg-white border border-white rounded-2xl w-1/6 h-3/4'></div>
            <div className='bg-white border border-white rounded-2xl w-1/6 h-3/4'></div>
        </div>
    </div>
  )
}

export default Metrics