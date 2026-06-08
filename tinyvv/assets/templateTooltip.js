dagcomponentfuncs.CustomTooltip_REPLACE = function (props) {
    return React.createElement(
        'div',
        {
            style: {
                border: '5px double',
                backgroundColor: props.color || 'grey',
                padding: 10,
            },
        },
        [
            // Example: React.createElement('div', {}, 'reference: ' + props.data.reference),
INSERT_HERE
        ]
    );
};
